"""
Mem0 魔改版 — 小说记忆引擎（轻量裁剪）

基于 Mem0 源码 (reference/mem0/) 裁剪改造：
- 复用 scoring.py 的混合评分算法
- 复用 configs/base.py 的数据结构设计
- SQLite + FTS5 替代向量存储（去掉了23+种向量库）
- BGE Small 本地 embedding（去掉了13+种embedding provider）
- 无 LLM 依赖，所有实体提取由 SMTS 侧完成

改造点（v3方案）：
- ✅ hash 去重
- ✅ 实体关系图
- ✅ BM25 (FTS5) + 语义 embedding + importance 混合评分
- ✅ 章节感知加权（临近章节加分）
- 🏗 分类过滤检索
- 🏗 关联记忆扩散
"""

import hashlib
import json
import math
import os
import sqlite3
import threading
import time
from datetime import datetime
from typing import Any, Optional

# ---------------------------------------------------------------------------
# 复用 Mem0 评分算法
# ---------------------------------------------------------------------------
import sys

_REF_SCORING = os.path.join(os.path.dirname(__file__),
                            "../../reference/mem0/mem0/mem0/utils/scoring.py")
if os.path.exists(_REF_SCORING):
    import importlib.util
    spec = importlib.util.spec_from_file_location("mem0_scoring", _REF_SCORING)
    mem0_scoring = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mem0_scoring)
    score_and_rank = mem0_scoring.score_and_rank
    normalize_bm25 = mem0_scoring.normalize_bm25
    get_bm25_params = mem0_scoring.get_bm25_params
    ENTITY_BOOST_WEIGHT = mem0_scoring.ENTITY_BOOST_WEIGHT
else:
    # 降级：内联简化版
    def normalize_bm25(raw, midpoint=7.0, steepness=0.6):
        return 1.0 / (1.0 + math.exp(-steepness * (raw - midpoint)))

    def get_bm25_params(query):
        terms = len(query.split()) if query else 1
        if terms <= 3: return 5.0, 0.7
        elif terms <= 6: return 7.0, 0.6
        else: return 10.0, 0.5

    ENTITY_BOOST_WEIGHT = 0.5

    def score_and_rank(semantic_results, bm25_results, query, entity_weight, top_k=10):
        """简化版混合评分"""
        scores = {}
        for r in semantic_results:
            scores[r["id"]] = {"semantic": r.get("score", 0), "bm25": 0, "entity_bonus": 0, "item": r}
        for r in bm25_results:
            if r["id"] in scores:
                scores[r["id"]]["bm25"] = r.get("score", 0)
            else:
                scores[r["id"]] = {"semantic": 0, "bm25": r.get("score", 0), "entity_bonus": 0, "item": r}
        results = []
        for mem_id, s in scores.items():
            combined = 0.5 * s["semantic"] + 0.3 * s["bm25"] + 0.2 * s["entity_bonus"]
            s["item"]["score"] = combined
            results.append(s["item"])
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]


# ---------------------------------------------------------------------------
# Embedding 引擎
# ---------------------------------------------------------------------------

_EMBEDDER = None
_EMBED_LOCK = threading.Lock()


def get_embedder():
    global _EMBEDDER
    if _EMBEDDER is not None:
        return _EMBEDDER
    with _EMBED_LOCK:
        if _EMBEDDER is not None:
            return _EMBEDDER
        try:
            from fastembed import TextEmbedding
            _EMBEDDER = TextEmbedding(model_name="BAAI/bge-small-zh-v1.5")
        except Exception as e:
            print(f"[mem0] WARNING: Failed to load BGE Small: {e}", flush=True)
            _EMBEDDER = None
        return _EMBEDDER


def embed_text(text: str):
    """返回 384-dim 向量（或空列表）"""
    model = get_embedder()
    if model is None:
        return []
    try:
        vec = list(model.embed(text))[0]
        return vec.tolist()
    except Exception:
        return []


# ---------------------------------------------------------------------------
# MemoryDB — SQLite + FTS5 + 实体图
# ---------------------------------------------------------------------------

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS memories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash TEXT    NOT NULL UNIQUE,
    memory      TEXT    NOT NULL,
    node_type   TEXT    NOT NULL DEFAULT 'episodic',
    chapter     INTEGER NOT NULL DEFAULT 0,
    entities    TEXT    DEFAULT '[]',
    importance  REAL    DEFAULT 0.5,
    category    TEXT    DEFAULT '',
    embedding   BLOB,
    created_at  TEXT    DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    memory, entities, content='memories', content_rowid='id'
);

CREATE TABLE IF NOT EXISTS entity_graph (
    entity      TEXT    PRIMARY KEY,
    related     TEXT    DEFAULT '[]',
    relations   TEXT    DEFAULT '{}',
    last_seen   INTEGER DEFAULT 0,
    mention_count INTEGER DEFAULT 0
);
"""


class MemoryDB:
    """单 Sqlite 记忆引擎"""

    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self):
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript(_CREATE_SQL)
        conn.commit()

    # --- 写入 ---

    def add_memory(self, memory: str, node_type: str = "episodic",
                   chapter: int = 0, entities: list = None,
                   importance: float = 0.5, category: str = "") -> tuple:
        """返回 (mem_id, content_hash, deduped)"""
        entities = entities or []
        content_hash = hashlib.md5(
            f"{memory}|{chapter}|{node_type}".encode()
        ).hexdigest()

        conn = self._get_conn()
        existing = conn.execute(
            "SELECT id FROM memories WHERE content_hash = ?", (content_hash,)
        ).fetchone()
        if existing:
            return existing["id"], content_hash, True

        # 算 embedding
        emb = embed_text(memory)
        emb_blob = json.dumps(emb).encode() if emb else None

        conn.execute(
            "INSERT INTO memories (content_hash, memory, node_type, chapter, entities, importance, category, embedding) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (content_hash, memory, node_type, chapter, json.dumps(entities, ensure_ascii=False),
             importance, category, emb_blob)
        )
        conn.commit()
        cur = conn.execute("SELECT last_insert_rowid()")
        last_id = cur.fetchone()[0]

        # 同步 FTS 索引
        try:
            conn.execute(
                "INSERT INTO memories_fts (rowid, memory, entities) VALUES (?, ?, ?)",
                (last_id, memory, " ".join(entities))
            )
        except Exception:
            pass

        # 更新实体图
        self.update_entity_graph(entities, chapter)
        conn.commit()
        return last_id, content_hash, False

    # --- 实体图 ---

    def update_entity_graph(self, entities: list, chapter: int):
        if not entities:
            return
        conn = self._get_conn()
        for e in entities:
            row = conn.execute("SELECT * FROM entity_graph WHERE entity = ?", (e,)).fetchone()
            if row:
                related = json.loads(row["related"])
                for other in entities:
                    if other != e and other not in related:
                        related.append(other)
                conn.execute(
                    "UPDATE entity_graph SET related=?, last_seen=?, mention_count=mention_count+1 WHERE entity=?",
                    (json.dumps(related, ensure_ascii=False), chapter, e)
                )
            else:
                related = [o for o in entities if o != e]
                conn.execute(
                    "INSERT INTO entity_graph (entity, related, relations, last_seen, mention_count) VALUES (?, ?, '{}', ?, 1)",
                    (e, json.dumps(related, ensure_ascii=False), chapter)
                )
        conn.commit()

    # --- BM25 搜索 ---

    def _search_fts(self, query: str, top_k: int) -> list[dict]:
        conn = self._get_conn()
        # 分词（FTS5 自动分词中文）
        q_clean = " OR ".join(query.strip().split())
        if not q_clean:
            return []
        rows = conn.execute(
            "SELECT m.id, m.memory, m.node_type, m.chapter, m.entities, m.importance, m.category, "
            "  rank "
            "FROM memories_fts f JOIN memories m ON f.rowid = m.id "
            "WHERE memories_fts MATCH ? "
            "ORDER BY rank LIMIT ?",
            (q_clean, top_k * 3)
        ).fetchall()
        results = []
        for r in rows:
            midpoint, steepness = get_bm25_params(query)
            raw = r["rank"]
            norm = normalize_bm25(abs(raw), midpoint, steepness) if raw else 0
            try:
                ents = json.loads(r["entities"]) if isinstance(r["entities"], str) else (r["entities"] or [])
            except Exception:
                ents = []
            results.append({
                "id": r["id"],
                "memory": r["memory"],
                "node_type": r["node_type"],
                "chapter": r["chapter"],
                "entities": ents,
                "importance": r["importance"],
                "category": r["category"],
                "score": norm,
            })
        return results

    # --- 语义搜索 ---

    def _search_semantic(self, query: str, top_k: int) -> list[dict]:
        query_emb = embed_text(query)
        if not query_emb:
            return []

        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, memory, node_type, chapter, entities, importance, category, embedding "
            "FROM memories ORDER BY chapter DESC LIMIT 200"
        ).fetchall()

        results = []
        for r in rows:
            emb_blob = r["embedding"]
            if not emb_blob:
                continue
            try:
                stored_emb = json.loads(emb_blob.decode() if isinstance(emb_blob, bytes) else emb_blob)
            except Exception:
                continue
            # 余弦相似度（向量已归一化）
            sim = sum(a * b for a, b in zip(query_emb, stored_emb))
            try:
                ents = json.loads(r["entities"]) if isinstance(r["entities"], str) else (r["entities"] or [])
            except Exception:
                ents = []
            results.append({
                "id": r["id"],
                "memory": r["memory"],
                "node_type": r["node_type"],
                "chapter": r["chapter"],
                "entities": ents,
                "importance": r["importance"],
                "category": r["category"],
                "score": sim,
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k * 3]

    # --- 混合搜索 ---

    def search(self, query: str, top_k: int = 10,
               exclude_chapters: list[int] = None,
               entity_weights: dict[str, float] = None,
               current_chapter: int = 0) -> list[dict]:
        """
混合搜索：BM25 + 语义 + importance + 章节感知加权
        :param current_chapter: 当前写作的章号，用于临近加权。0=不启用。"""
        exclude_chapters = exclude_chapters or []
        entity_weights = entity_weights or {}

        # 双通道检索
        bm25_results = self._search_fts(query, top_k)
        semantic_results = self._search_semantic(query, top_k)

        # 合并评分
        combined = {}
        for r in bm25_results:
            if r["chapter"] in exclude_chapters:
                continue
            combined[r["id"]] = {
                "item": r,
                "bm25": r["score"],
                "semantic": 0.0,
                "entity_bonus": 0.0,
            }

        for r in semantic_results:
            if r["chapter"] in exclude_chapters:
                continue
            if r["id"] in combined:
                combined[r["id"]]["semantic"] = r["score"]
            else:
                combined[r["id"]] = {
                    "item": r,
                    "bm25": 0.0,
                    "semantic": r["score"],
                    "entity_bonus": 0.0,
                }

        # 章节感知加权（离当前写作章越近权重越高）
        current = current_chapter if current_chapter > 0 else max(
            (s["item"]["chapter"] for s in combined.values() if s["item"]["chapter"]),
            default=0
        )

        results = []
        for mem_id, s in combined.items():
            item = s["item"]
            # 章节权重：离当前章越近越高
            ch_dist = current - item["chapter"] if current > 0 else 0
            chapter_weight = max(0.5, 1.0 - ch_dist * 0.05) if ch_dist > 0 else 1.0

            # 实体权重
            ent_bonus = 0.0
            for e in item["entities"]:
                w = entity_weights.get(e, 0)
                if w > 0:
                    ent_bonus += w * ENTITY_BOOST_WEIGHT

            # 综合评分
            combined_score = (
                0.35 * s["semantic"] +
                0.25 * s["bm25"] +
                0.20 * item["importance"] +
                0.10 * ent_bonus
            ) * chapter_weight

            item["score"] = round(combined_score, 4)
            results.append(item)

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    # --- 查询 ---

    def count(self) -> int:
        row = self._get_conn().execute("SELECT COUNT(*) as c FROM memories").fetchone()
        return row["c"] if row else 0

    def list_memories(self, limit: int = 100, offset: int = 0) -> tuple:
        rows = self._get_conn().execute(
            "SELECT id, memory, node_type, chapter, entities, importance, category, created_at "
            "FROM memories ORDER BY chapter DESC, id DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
        total = self.count()
        memories = []
        for r in rows:
            try:
                ents = json.loads(r["entities"]) if isinstance(r["entities"], str) else (r["entities"] or [])
            except Exception:
                ents = []
            memories.append({
                "id": r["id"],
                "memory": r["memory"],
                "node_type": r["node_type"],
                "chapter": r["chapter"],
                "entities": ents,
                "importance": r["importance"],
                "category": r["category"],
                "created_at": r["created_at"],
            })
        return memories, total

    def get_entity_graph(self) -> list[dict]:
        rows = self._get_conn().execute("SELECT * FROM entity_graph ORDER BY mention_count DESC LIMIT 200").fetchall()
        result = {}
        for r in rows:
            try:
                related = json.loads(r["related"]) if isinstance(r["related"], str) else (r["related"] or [])
            except Exception:
                related = []
            try:
                relations = json.loads(r["relations"]) if isinstance(r["relations"], str) else (r["relations"] or {})
            except Exception:
                relations = {}
            result[r["entity"]] = {
                "related": related,
                "relations": relations,
                "last_seen": r["last_seen"],
                "mention_count": r["mention_count"],
            }
        return result

    def delete_memory(self, mem_id: int) -> bool:
        conn = self._get_conn()
        conn.execute("DELETE FROM memories WHERE id = ?", (mem_id,))
        conn.execute("DELETE FROM memories_fts WHERE rowid = ?", (mem_id,))
        conn.commit()
        return True

    # --- 关联扩散（P1） ---

    def expand_by_entities(self, entities: list[str], top_k: int = 5) -> list[dict]:
        """搜到一条记忆后，顺着实体链拉相关记忆"""
        if not entities:
            return []
        conn = self._get_conn()
        # 从实体图找关联实体
        related_entities = set(entities)
        for e in entities:
            row = conn.execute("SELECT related FROM entity_graph WHERE entity = ?", (e,)).fetchone()
            if row:
                try:
                    for re in json.loads(row["related"]):
                        related_entities.add(re)
                except Exception:
                    pass

        # 检索这些实体相关的记忆
        placeholders = ",".join("?" for _ in related_entities)
        rows = conn.execute(
            f"SELECT id, memory, node_type, chapter, entities, importance, category "
            f"FROM memories WHERE id IN ("
            f"  SELECT id FROM memories WHERE "
            f"  {' OR '.join('entities LIKE ?' for _ in related_entities)}"
            f") ORDER BY chapter DESC LIMIT ?",
            [f'%{e}%' for e in related_entities] + [top_k]
        ).fetchall()

        results = []
        for r in rows:
            try:
                ents = json.loads(r["entities"]) if isinstance(r["entities"], str) else (r["entities"] or [])
            except Exception:
                ents = []
            results.append({
                "id": r["id"],
                "memory": r["memory"],
                "node_type": r["node_type"],
                "chapter": r["chapter"],
                "entities": ents,
                "importance": r["importance"],
                "category": r["category"],
                "score": 0.5,  # 默认分，让LLM自己判断
            })
        return results

    # --- 记忆合并（P1） ---

    def merge_similar(self, threshold: float = 0.92) -> dict:
        # 扫描所有记忆，合并 embedding 相似度超过 threshold 的条目。
        # 保留重要度更高的那条，删除另一条。
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, memory, embedding, importance FROM memories WHERE embedding IS NOT NULL ORDER BY id"
        ).fetchall()

        if len(rows) < 2:
            return {"merged": 0, "kept": len(rows)}

        # 反序列化 embedding
        mems = []
        for r in rows:
            try:
                emb = json.loads(r["embedding"].decode() if isinstance(r["embedding"], bytes) else r["embedding"])
                if emb:
                    mems.append({
                        "id": r["id"],
                        "memory": r["memory"],
                        "embedding": emb,
                        "importance": r["importance"],
                    })
            except Exception:
                pass

        if len(mems) < 2:
            return {"merged": 0, "kept": len(mems)}

        merged = set()
        deleted = set()
        for i in range(len(mems)):
            if mems[i]["id"] in deleted:
                continue
            for j in range(i + 1, len(mems)):
                if mems[j]["id"] in deleted:
                    continue
                # 余弦相似度（向量已归一化）
                emb_i = mems[i]["embedding"]
                emb_j = mems[j]["embedding"]
                dot = sum(a * b for a, b in zip(emb_i, emb_j))
                if dot >= threshold:
                    # 保留重要度更高的
                    if mems[i]["importance"] >= mems[j]["importance"]:
                        keep, remove = mems[i], mems[j]
                    else:
                        keep, remove = mems[j], mems[i]
                    deleted.add(remove["id"])
                    merged.add(keep["id"])

        # 执行删除
        for mid in deleted:
            try:
                conn.execute("DELETE FROM memories WHERE id = ?", (mid,))
                conn.execute("DELETE FROM memories_fts WHERE rowid = ?", (mid,))
            except Exception:
                pass
        conn.commit()

        return {
            "merged": len(deleted),
            "kept": len(mems) - len(deleted),
        }
