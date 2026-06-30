<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api.js';
  import { progress, addToast } from '../lib/stores.js';
  import { t } from '../lib/i18n/index.js';

  let sourceMode = 'native'; // native | mem0 | graph
  let viewMode = 'list'; // list | timeline
  let categoryFilter = 'all';
  let chapterFilter = 'all';

  // --- native ---
  const categoryKeys = ['character', 'location', 'item', 'event', 'promise', 'other'];
  const categoryBadge = {
    character: 'badge-primary',
    location: 'badge-secondary',
    item: 'badge-accent',
    event: 'badge-info',
    promise: 'badge-warning',
    other: 'badge-ghost',
  };

  $: entries = $progress?.memory_entries || [];
  $: maxTokens = $progress?.memory_max_tokens || 0;
  $: chapters = $progress?.chapters || [];
  $: chapterNums = [...new Set(entries.map(e => e.chapter).filter(Boolean))].sort((a, b) => a - b);
  $: categoryCounts = categoryKeys.reduce((acc, key) => {
    acc[key] = entries.filter(e => e.category === key).length;
    return acc;
  }, {});
  $: contentChars = entries.reduce((sum, e) => sum + [...(e.content || '')].length, 0);
  $: filtered = entries.filter(e => {
    if (categoryFilter !== 'all' && e.category !== categoryFilter) return false;
    if (chapterFilter !== 'all' && e.chapter !== Number(chapterFilter)) return false;
    return true;
  });
  $: timelineRows = buildTimeline(filtered);

  // --- mem0 ---
  let mem0Memories = [];
  let mem0Total = 0;
  let mem0Loading = false;
  let mem0Failed = false;
  let mem0Importing = false;
  let mem0Merging = false;
  let mem0Stats = { running: false, total: 0, entities: 0 };

  async function loadMem0() {
    mem0Loading = true;
    try {
      const [mems, stats] = await Promise.all([
        api('GET', '/api/memories/mem0'),
        api('GET', '/api/memories/mem0/stats').catch(() => ({ running: false })),
      ]);
      mem0Memories = mems?.memories || [];
      mem0Total = mems?.total || 0;
      mem0Stats = stats || { running: false };
    } catch (e) {
      mem0Failed = true;
      mem0Stats = { running: false };
      addToast(e.message, 'error');
    }
    mem0Loading = false;
  }

  async function deleteMem0Memory(memId) {
    try {
      await api('DELETE', `/api/memories/mem0/${memId}`);
      mem0Memories = mem0Memories.filter(m => m.id !== memId);
      mem0Total--;
      addToast($t('memory.mem0.deleted'), 'success');
    } catch (e) {
      addToast(e.message, 'error');
    }
  }

  async function batchImportMem0() {
    mem0Importing = true;
    try {
      const res = await api('POST', '/api/memories/mem0/import');
      addToast($t('memory.mem0.imported', { written: res.written, total: res.total }), 'success');
      loadMem0();
    } catch (e) {
      addToast(e.message, 'error');
    }
    mem0Importing = false;
  }

  async function mergeMem0Memories() {
    mem0Merging = true;
    try {
      const res = await api('POST', '/api/memories/mem0/merge');
      addToast($t('memory.mem0.merged', { n: res.merged, kept: res.kept }), 'success');
      loadMem0();
    } catch (e) {
      addToast(e.message, 'error');
    }
    mem0Merging = false;
  }

  $: if (sourceMode === 'mem0' && mem0Memories.length === 0 && !mem0Loading && !mem0Failed) {
    loadMem0();
  }

  // --- entity graph ---
  let graphData = { entities: {}, weights: {} };
  let graphLoading = false;
  let graphFailed = false;
  let graphCanvas = null;
  let graphNodes = [];
  let graphEdges = [];
  let graphAnim = null;
  let graphHovered = null;
  let graphContainer = null;

  async function loadGraph() {
    graphLoading = true;
    try {
      const [ents, stats] = await Promise.all([
        api('GET', '/api/memories/mem0/entities'),
        api('GET', '/api/memories/mem0/stats').catch(() => ({ running: false })),
      ]);
      if (stats?.running) {
        graphData = { entities: ents?.entities || {}, weights: {} };
        buildGraphLayout();
      } else {
        graphData = { entities: {}, weights: {} };
      }
    } catch (e) {
      graphFailed = true;
      graphData = { entities: {}, weights: {} };
    }
    graphLoading = false;
  }

  function buildGraphLayout() {
    const ents = graphData.entities;
    const keys = Object.keys(ents);
    if (keys.length === 0) return;

    // 根据容器尺寸动态设置画布
    const canvas = graphCanvas;
    if (graphContainer && canvas) {
      canvas.width = Math.max(graphContainer.clientWidth, 300);
      canvas.height = Math.max(graphContainer.clientHeight, 300);
    }

    // Normalize mention_count for node sizing
    const counts = keys.map(k => ents[k].mention_count || 1);
    const maxCount = Math.max(...counts);

    // 动态中心坐标
    const W = canvas?.width || 600;
    const H = canvas?.height || 500;
    const centerX = W / 2, centerY = H / 2;
    const radius = Math.min(centerX, centerY) - 40;
    graphNodes = keys.map((name, i) => ({
      name,
      mentionCount: ents[name].mention_count || 0,
      related: ents[name].related || [],
      size: 10 + 30 * ((ents[name].mention_count || 1) / maxCount),
      x: centerX + radius * Math.cos((2 * Math.PI * i) / keys.length),
      y: centerY + radius * Math.sin((2 * Math.PI * i) / keys.length),
      vx: 0, vy: 0,
    }));

    // Build edges from related
    const edgeSet = new Set();
    graphEdges = [];
    for (const node of graphNodes) {
      for (const rel of node.related) {
        const key = [node.name, rel].sort().join('||');
        if (!edgeSet.has(key) && keys.includes(rel)) {
          edgeSet.add(key);
          graphEdges.push({ source: node.name, target: rel });
        }
      }
    }

    // Simple force simulation (a few iterations)
    const nodeMap = {};
    for (const n of graphNodes) nodeMap[n.name] = n;

    for (let iter = 0; iter < 80; iter++) {
      // Repulsion between all nodes
      for (let i = 0; i < graphNodes.length; i++) {
        for (let j = i + 1; j < graphNodes.length; j++) {
          const a = graphNodes[i], b = graphNodes[j];
          let dx = b.x - a.x;
          let dy = b.y - a.y;
          let dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = 2000 / (dist * dist);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          a.vx -= fx; a.vy -= fy;
          b.vx += fx; b.vy += fy;
        }
      }
      // Attraction along edges
      for (const edge of graphEdges) {
        const a = nodeMap[edge.source], b = nodeMap[edge.target];
        if (!a || !b) continue;
        let dx = b.x - a.x;
        let dy = b.y - a.y;
        let dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = dist * 0.01;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        a.vx += fx; a.vy += fy;
        b.vx -= fx; b.vy -= fy;
      }
      // Center gravity
      for (const n of graphNodes) {
        n.vx += (centerX - n.x) * 0.005;
        n.vy += (centerY - n.y) * 0.005;
        n.x += n.vx;
        n.y += n.vy;
        n.vx *= 0.85;
        n.vy *= 0.85;
      }
    }

    // Render
    renderGraphCanvas();
  }

  function renderGraphCanvas() {
    const canvas = graphCanvas;
    if (!canvas || graphNodes.length === 0) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    const isDark = document.documentElement.classList.contains('dark') ||
      getComputedStyle(document.documentElement).getPropertyValue('color-scheme').trim() === 'dark';
    const nodeColor = isDark ? 'oklch(0.95 0.005 270)' : '#1a1a2e';
    const edgeColor = isDark ? 'oklch(1 0 0 / 0.12)' : '#ccc';
    const fillColor = isDark ? 'oklch(0.72 0.14 65 / 0.2)' : 'oklch(0.72 0.14 65 / 0.15)';
    const hoverColor = isDark ? 'oklch(0.72 0.14 65 / 0.5)' : 'oklch(0.72 0.14 65 / 0.3)';

    // Draw edges
    ctx.strokeStyle = edgeColor;
    ctx.lineWidth = 1;
    for (const edge of graphEdges) {
      const src = graphNodes.find(n => n.name === edge.source);
      const tgt = graphNodes.find(n => n.name === edge.target);
      if (!src || !tgt) continue;
      ctx.beginPath();
      ctx.moveTo(src.x, src.y);
      ctx.lineTo(tgt.x, tgt.y);
      ctx.stroke();
    }

    // Draw nodes
    for (const n of graphNodes) {
      const isHovered = graphHovered === n.name;
      const r = isHovered ? n.size + 4 : n.size;

      // Glow for hovered
      if (isHovered) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, r + 6, 0, Math.PI * 2);
        ctx.fillStyle = 'oklch(0.72 0.14 65 / 0.15)';
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
      ctx.fillStyle = isHovered ? hoverColor : fillColor;
      ctx.fill();
      ctx.strokeStyle = nodeColor;
      ctx.lineWidth = isHovered ? 2 : 1;
      ctx.stroke();

      // Label
      const fontSize = Math.max(10, Math.min(14, n.size * 0.5));
      ctx.font = `${fontSize}px Inter, ui-sans-serif, system-ui, sans-serif`;
      ctx.textAlign = 'center';
      ctx.fillStyle = nodeColor;
      ctx.fillText(n.name, n.x, n.y + r + fontSize + 2);
    }

    // Hover info
    if (graphHovered) {
      const n = graphNodes.find(x => x.name === graphHovered);
      if (n) {
        ctx.font = '11px Inter, ui-sans-serif, system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillStyle = 'oklch(0.95 0.005 270 / 0.6)';
        ctx.fillText(`出现 ${n.mentionCount} 次 · 关联 ${n.related.length} 个实体`, n.x, n.y + r + fontSize + 16);
      }
    }
  }

  function onGraphMouseMove(e) {
    const rect = graphCanvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const dpr = graphCanvas.width / rect.width;
    const px = mx * dpr, py = my * dpr;

    let found = null;
    for (const n of graphNodes) {
      const dx = px - n.x, dy = py - n.y;
      if (dx * dx + dy * dy < (n.size + 8) * (n.size + 8)) {
        found = n.name;
        break;
      }
    }
    if (found !== graphHovered) {
      graphHovered = found;
      renderGraphCanvas();
    }
  }

  function onGraphResize() {
    if (!graphCanvas) return;
    const rect = graphCanvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    graphCanvas.width = rect.width * dpr;
    graphCanvas.height = 500 * dpr;
    graphCanvas.style.width = rect.width + 'px';
    graphCanvas.style.height = '500px';
    if (graphNodes.length > 0) renderGraphCanvas();
  }

  $: if (sourceMode === 'graph' && Object.keys(graphData.entities).length === 0 && !graphLoading && !graphFailed) {
    loadGraph();
  }

  // --- common ---
  function extractSnippet(chapterNum, position, maxRunes = 100) {
    if (!position || !chapterNum) return '';
    const ch = chapters.find(c => c.num === chapterNum);
    if (!ch?.content) return '';
    const paragraphs = ch.content.split('\n\n');
    const idx = position - 1;
    if (idx < 0 || idx >= paragraphs.length) return '';
    const para = paragraphs[idx].trim();
    const runes = [...para];
    if (runes.length > maxRunes) return runes.slice(0, maxRunes).join('') + '…';
    return para;
  }

  function buildTimeline(items) {
    const byChapter = new Map();
    for (const e of items) {
      const n = e.chapter || 0;
      if (!byChapter.has(n)) byChapter.set(n, []);
      byChapter.get(n).push(e);
    }
    return [...byChapter.entries()]
      .sort((a, b) => a[0] - b[0])
      .map(([num, list]) => ({
        num,
        title: chapters.find(c => c.num === num)?.title || '',
        entries: [...list].sort((a, b) => a.id - b.id),
      }));
  }

  function formatEntryLine(e) {
    const snippet = extractSnippet(e.chapter, e.position);
    if (snippet) {
      return `[第${e.chapter}章] ${e.content}（原文：「${snippet}」）`;
    }
    return `[第${e.chapter}章] ${e.content}`;
  }

  async function refreshProgress() {
    try {
      progress.set(await api('GET', '/api/progress'));
      addToast($t('memory.refreshed'), 'success');
    } catch (e) {
      addToast(e.message, 'error');
    }
  }

  async function copyAll() {
    if (entries.length === 0) return;
    const text = entries.map(formatEntryLine).join('\n');
    try {
      await navigator.clipboard.writeText(text);
      addToast($t('memory.copy.done'), 'success');
    } catch (e) {
      addToast($t('memory.copy.failed'), 'error');
    }
  }

  onMount(() => {
    if (sourceMode === 'graph') {
      setTimeout(() => {
        onGraphResize();
        if (graphNodes.length > 0) renderGraphCanvas();
      }, 100);
    }
  });
</script>

<div class="space-y-4">
  <!-- Header -->
  <div class="card bg-base-200 shadow-sm">
    <div class="card-body py-4 gap-3">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h2 class="card-title text-base">{$t('memory.title')}</h2>
        <div class="flex flex-wrap gap-2">
          {#if sourceMode === 'native'}
            <button class="btn btn-ghost btn-sm" on:click={refreshProgress}>{$t('common.refresh')}</button>
            <button class="btn btn-outline btn-sm" disabled={entries.length === 0} on:click={copyAll}>
              {$t('common.copy')}
            </button>
          {:else if sourceMode === 'mem0'}
            <button class="btn btn-ghost btn-sm" on:click={loadMem0} disabled={mem0Loading}>
              {mem0Loading ? $t('memory.mem0.loading') : $t('common.refresh')}
            </button>
            <button class="btn btn-outline btn-sm" on:click={batchImportMem0} disabled={mem0Importing}>
              {mem0Importing ? $t('memory.mem0.importing') : $t('memory.mem0.import')}
            </button>
            <button class="btn btn-outline btn-sm" on:click={mergeMem0Memories} disabled={mem0Merging}>
              {mem0Merging ? $t('memory.mem0.merging') : $t('memory.mem0.merge')}
            </button>
          {:else if sourceMode === 'graph'}
            <button class="btn btn-ghost btn-sm" on:click={loadGraph} disabled={graphLoading}>
              {graphLoading ? '加载中…' : $t('common.refresh')}
            </button>
          {/if}
        </div>
      </div>
      <!-- Source tabs -->
      <div class="tabs tabs-boxed tabs-sm">
        <button class="tab {sourceMode === 'native' ? 'tab-active' : ''}" on:click={() => sourceMode = 'native'}>
          {$t('memory.source.native')}
        </button>
        <button class="tab {sourceMode === 'mem0' ? 'tab-active' : ''}" on:click={() => sourceMode = 'mem0'}>
          {$t('memory.source.mem0')}
          {#if !mem0Stats.running}
            <span class="loading loading-spinner loading-xs ml-1"></span>
          {/if}
        </button>
        <button class="tab {sourceMode === 'graph' ? 'tab-active' : ''}" on:click={() => { sourceMode = 'graph'; onGraphResize(); }}>
          实体图谱
          {#if graphLoading}
            <span class="loading loading-spinner loading-xs ml-1"></span>
          {/if}
        </button>
      </div>
      <!-- Stats -->
      <div class="flex flex-wrap gap-2 text-sm">
        {#if sourceMode === 'native'}
          <span class="badge badge-ghost">{$t('memory.stats.total', { n: entries.length })}</span>
          <span class="badge badge-outline">{$t('memory.stats.chapters', { n: chapterNums.length })}</span>
          {#if maxTokens > 0}
            <span class="badge badge-outline">{$t('memory.stats.budget', { n: maxTokens })}</span>
          {/if}
          {#if contentChars > 0}
            <span class="badge badge-outline">{$t('memory.stats.chars', { n: contentChars })}</span>
          {/if}
        {:else if sourceMode === 'mem0'}
          <span class="badge" class:badge-success={mem0Stats.running} class:badge-error={!mem0Stats.running}>
            {mem0Stats.running ? $t('memory.mem0.online') : $t('memory.mem0.offline')}
          </span>
          <span class="badge badge-ghost">{$t('memory.stats.total', { n: mem0Total })}</span>
          {#if mem0Stats.entities > 0}
            <span class="badge badge-outline">{$t('memory.mem0.entities', { n: mem0Stats.entities })}</span>
          {/if}
        {:else if sourceMode === 'graph'}
          <span class="badge badge-ghost">实体 {Object.keys(graphData.entities).length} 个</span>
          <span class="badge badge-outline">关联 {graphEdges.length} 条</span>
        {/if}
      </div>
    </div>
  </div>

  <!-- Entity graph content -->
  {#if sourceMode === 'graph'}
    {#if graphLoading}
      <div class="card bg-base-200 shadow-sm">
        <div class="card-body py-10 text-center">
          <span class="loading loading-spinner loading-lg"></span>
        </div>
      </div>
    {:else if Object.keys(graphData.entities).length === 0}
      <div class="card bg-base-200 shadow-sm">
        <div class="card-body py-10 text-center">
          <p class="text-base-content/50">暂无实体数据，开始写作后将自动生成实体关系图</p>
        </div>
      </div>
    {:else}
      <div class="card bg-base-200 shadow-sm">
        <div class="card-body py-4">
          <div class="graph-container" bind:this={graphContainer} style="min-height:300px"> 
            <canvas
              bind:this={graphCanvas}
              class="w-full h-full block"
              on:mousemove={onGraphMouseMove}
              on:mouseleave={() => { graphHovered = null; renderGraphCanvas(); }}
            ></canvas>
          </div>
          <!-- Entity weight list -->
          <div class="mt-4 space-y-2">
            <h3 class="text-sm font-medium text-base-content/70">实体权重</h3>
            <div class="grid grid-cols-2 gap-2">
              {#each [...graphNodes].sort((a, b) => b.mentionCount - a.mentionCount) as node}
                <div class="flex items-center gap-2 px-3 py-1.5 rounded-md bg-base-300/40">
                  <span class="text-sm font-medium min-w-[4em]">{node.name}</span>
                  <div class="flex-1 h-2 rounded-full bg-base-300 overflow-hidden">
                    <div
                      class="h-full rounded-full bg-primary/60 transition-all duration-300"
                      style="width: {Math.min(100, (node.mentionCount / Math.max(...graphNodes.map(n => n.mentionCount))) * 100)}%"
                    ></div>
                  </div>
                  <span class="text-xs text-base-content/40 w-8 text-right">{node.mentionCount}</span>
                </div>
              {/each}
            </div>
          </div>
        </div>
      </div>
    {/if}

  <!-- Mem0 content -->
  {:else if sourceMode === 'mem0'}
    {#if mem0Loading}
      <div class="card bg-base-200 shadow-sm">
        <div class="card-body py-10 text-center">
          <span class="loading loading-spinner loading-lg"></span>
        </div>
      </div>
    {:else if !mem0Stats.running}
      <div class="card bg-base-200 shadow-sm">
        <div class="card-body py-10 text-center gap-2">
          <p class="font-medium text-base-content/70">{$t('memory.mem0.unavailable.title')}</p>
          <p class="text-sm text-base-content/50">{$t('memory.mem0.unavailable.hint')}</p>
        </div>
      </div>
    {:else if mem0Memories.length === 0}
      <div class="card bg-base-200 shadow-sm">
        <div class="card-body py-10 text-center">
          <p class="text-base-content/50">{$t('memory.mem0.empty')}</p>
        </div>
      </div>
    {:else}
      <div class="card bg-base-200 shadow-sm">
        <div class="card-body py-4 gap-3">
          <div class="overflow-x-auto">
            <table class="table table-sm">
              <thead>
                <tr>
                  <th>{$t('memory.col.id')}</th>
                  <th>{$t('memory.col.chapter')}</th>
                  <th>{$t('memory.col.category')}</th>
                  <th>{$t('memory.col.content')}</th>
                  <th>{$t('memory.col.entities')}</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {#each mem0Memories as m (m.id)}
                  <tr>
                    <td class="font-mono text-xs">{m.id}</td>
                    <td>{$t('memory.chapterLabel', { n: m.chapter })}</td>
                    <td>
                      <span class="badge badge-xs badge-ghost">{m.category}</span>
                    </td>
                    <td class="max-w-md">{m.memory}</td>
                    <td class="text-xs">
                      {#if m.entities?.length}
                        {#each m.entities as e}
                          <span class="badge badge-xs badge-outline mr-0.5">{e}</span>
                        {/each}
                      {:else}
                        <span class="text-base-content/30">—</span>
                      {/if}
                    </td>
                    <td>
                      <button class="btn btn-ghost btn-xs text-error" on:click={() => deleteMem0Memory(m.id)}>
                        {$t('common.delete')}
                      </button>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    {/if}

  <!-- Native content -->
  {:else if entries.length === 0}
    <div class="card bg-base-200 shadow-sm">
      <div class="card-body py-10 text-center gap-2">
        <p class="font-medium text-base-content/70">{$t('memory.empty.title')}</p>
        <p class="text-sm text-base-content/50 max-w-lg mx-auto">{$t('memory.empty.hint')}</p>
      </div>
    </div>
  {:else}
    <div class="card bg-base-200 shadow-sm">
      <div class="card-body py-4 gap-3">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="tabs tabs-boxed tabs-sm">
            <button class="tab {viewMode === 'list' ? 'tab-active' : ''}" on:click={() => viewMode = 'list'}>
              {$t('memory.tabs.list')}
            </button>
            <button class="tab {viewMode === 'timeline' ? 'tab-active' : ''}" on:click={() => viewMode = 'timeline'}>
              {$t('memory.tabs.timeline')}
            </button>
          </div>
          <div class="flex flex-wrap gap-2">
            <select class="select select-bordered select-xs" bind:value={categoryFilter}>
              <option value="all">{$t('memory.filter.allCategories')}</option>
              {#each categoryKeys as key}
                {#if categoryCounts[key] > 0}
                  <option value={key}>{$t('memory.category.' + key)} ({categoryCounts[key]})</option>
                {/if}
              {/each}
            </select>
            <select class="select select-bordered select-xs" bind:value={chapterFilter}>
              <option value="all">{$t('memory.filter.allChapters')}</option>
              {#each chapterNums as num}
                <option value={num}>{$t('memory.chapterLabel', { n: num })}</option>
              {/each}
            </select>
          </div>
        </div>

        {#if filtered.length === 0}
          <p class="text-sm text-base-content/50 py-6 text-center">{$t('memory.filter.noMatch')}</p>
        {:else if viewMode === 'list'}
          <div class="overflow-x-auto">
            <table class="table table-sm">
              <thead>
                <tr>
                  <th>{$t('memory.col.id')}</th>
                  <th>{$t('memory.col.category')}</th>
                  <th>{$t('memory.col.chapter')}</th>
                  <th>{$t('memory.col.position')}</th>
                  <th>{$t('memory.col.content')}</th>
                  <th>{$t('memory.col.snippet')}</th>
                </tr>
              </thead>
              <tbody>
                {#each filtered as e (e.id)}
                  {@const snippet = extractSnippet(e.chapter, e.position)}
                  <tr>
                    <td class="font-mono text-xs">{e.id}</td>
                    <td>
                      <span class="badge badge-xs {categoryBadge[e.category] || 'badge-ghost'}">
                        {$t('memory.category.' + (e.category || 'other'))}
                      </span>
                    </td>
                    <td>{$t('memory.chapterLabel', { n: e.chapter })}</td>
                    <td class="text-base-content/60">{e.position > 0 ? e.position : '—'}</td>
                    <td class="max-w-md">{e.content}</td>
                    <td class="text-xs text-base-content/60 max-w-xs whitespace-normal">
                      {#if snippet}
                        「{snippet}」
                      {:else}
                        <span class="text-base-content/30">—</span>
                      {/if}
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {:else}
          <div class="space-y-3">
            {#each timelineRows as row}
              <div class="rounded-lg bg-base-300/40 p-3">
                <div class="font-medium text-sm mb-2">
                  {$t('memory.timeline.chapter', { n: row.num })}
                  {#if row.title}
                    <span class="text-base-content/50 font-normal">· {row.title}</span>
                  {/if}
                  <span class="badge badge-xs badge-ghost ml-1">{row.entries.length}</span>
                </div>
                <div class="space-y-2">
                  {#each row.entries as e (e.id)}
                    {@const snippet = extractSnippet(e.chapter, e.position)}
                    <div class="rounded-md bg-base-200/80 px-3 py-2 text-sm">
                      <div class="flex flex-wrap items-center gap-2 mb-1">
                        <span class="font-mono text-xs text-base-content/50">#{e.id}</span>
                        <span class="badge badge-xs {categoryBadge[e.category] || 'badge-ghost'}">
                          {$t('memory.category.' + (e.category || 'other'))}
                        </span>
                        {#if e.position > 0}
                          <span class="text-xs text-base-content/40">{$t('memory.positionLabel', { n: e.position })}</span>
                        {/if}
                      </div>
                      <div>{e.content}</div>
                      {#if snippet}
                        <div class="text-xs text-base-content/50 mt-1">{$t('memory.snippetLabel')}：「{snippet}」</div>
                      {/if}
                    </div>
                  {/each}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>
