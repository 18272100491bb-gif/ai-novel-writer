#!/usr/bin/env python3
"""
Mem0 魔改版 — FastAPI HTTP sidecar
基于 Mem0 源码裁剪改造，替换 Kioku。

API:
  GET  /health
  POST /api/add
  POST /api/search
  GET  /api/memories/{project_id}
  GET  /api/entity_graph/{project_id}
  DELETE /api/memory/{project_id}/{mem_id}
"""

import argparse
import json
import os
import sys
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 把 engine.py 所在的目录加入路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import MemoryDB

app = FastAPI(title="Mem0 Sidecar (Novel Edition)")

# 项目 ID → MemoryDB 实例
_DBS: dict[str, MemoryDB] = {}
_DATA_DIR = ""


def get_db(project_id: str) -> MemoryDB:
    if project_id not in _DBS:
        db_dir = os.path.join(_DATA_DIR, project_id, ".mem0")
        os.makedirs(db_dir, exist_ok=True)
        _DBS[project_id] = MemoryDB(os.path.join(db_dir, "mem0.db"))
    return _DBS[project_id]


# ---------------------------------------------------------------------------
# 请求/响应模型
# ---------------------------------------------------------------------------

class AddRequest(BaseModel):
    project_id: str
    memory: str
    node_type: str = "episodic"
    entities: list[str] = []
    chapter: int = 0
    emotion: Optional[str] = None
    importance: float = 0.5
    category: str = ""


class AddResponse(BaseModel):
    id: int
    hash: str
    deduped: bool


class SearchRequest(BaseModel):
    project_id: str
    query: str
    top_k: int = 10
    exclude_chapters: list[int] = []
    weights: Optional[dict[str, float]] = None


class SearchResult(BaseModel):
    id: int
    memory: str
    node_type: str
    chapter: int
    entities: list[str]
    importance: float
    category: str
    score: float


class SearchResponse(BaseModel):
    results: list[SearchResult]


class EntityGraphResponse(BaseModel):
    entities: dict


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "memory_count": sum(
        db.count() for db in _DBS.values()
    )}


@app.post("/api/add", response_model=AddResponse)
def add_memory(req: AddRequest):
    db = get_db(req.project_id)
    try:
        mem_id, mem_hash, deduped = db.add_memory(
            memory=req.memory,
            node_type=req.node_type,
            chapter=req.chapter,
            entities=req.entities,
            importance=req.importance,
            category=req.category,
        )
        return AddResponse(id=mem_id, hash=mem_hash, deduped=deduped)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search", response_model=SearchResponse)
def search_memory(req: SearchRequest):
    db = get_db(req.project_id)
    try:
        results = db.search(
            query=req.query,
            top_k=req.top_k,
            exclude_chapters=req.exclude_chapters,
            entity_weights=req.weights,
        )
        return SearchResponse(
            results=[SearchResult(**r) for r in results]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memories/{project_id}")
def list_memories(project_id: str, limit: int = 100, offset: int = 0):
    db = get_db(project_id)
    try:
        memories, total = db.list_memories(limit=limit, offset=offset)
        return {"memories": memories, "total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/entity_graph/{project_id}")
def get_entity_graph(project_id: str):
    db = get_db(project_id)
    try:
        entities = db.get_entity_graph()
        return EntityGraphResponse(entities=entities)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/memory/{project_id}/{mem_id}")
def delete_memory(project_id: str, mem_id: int):
    db = get_db(project_id)
    try:
        db.delete_memory(mem_id)
        return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# 启动
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mem0 Sidecar")
    parser.add_argument("--port", type=int, default=49152)
    parser.add_argument("--data-dir", type=str, default="./storys")
    args = parser.parse_args()

    _DATA_DIR = args.data_dir
    print(f"[mem0] Starting on port {args.port}, data dir: {_DATA_DIR}", flush=True)

    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")
