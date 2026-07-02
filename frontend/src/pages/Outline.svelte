<script>
  import { api } from '../lib/api.js';
  import { progress, config, streamingContent, streamingChapterIdx, taskRunning, addToast, showConfirm, continueAnalysis, outlineCharacterSuggestions, outlineCharacterShowSuggestions, settings } from '../lib/stores.js';
  import { t } from '../lib/i18n/index.js';
  import ConfigChangePanel from '../components/ConfigChangePanel.svelte';

  $: p = $progress;
  $: displayTitle = $config?.story?.title || p?.title || '';
  $: displaySynopsis = $config?.story?.story_synopsis || p?.story_synopsis || '';
  $: chapters = p?.chapters || [];
  $: hasOutline = chapters.length > 0;
  $: hasAccepted = chapters.some(c => c.status === 'accepted');
  $: inOutlinePhase = p?.phase === 'outline';
  $: pendingCount = chapters.filter(c => c.status === 'pending').length;

  $: statusMeta = {
    pending:  { label: $t('outline.status.pending'),  cls: 'badge-ghost' },
    writing:  { label: $t('outline.status.writing'),  cls: 'badge-warning' },
    review:   { label: $t('outline.status.review'),   cls: 'badge-info' },
    accepted: { label: $t('outline.status.accepted'), cls: 'badge-success' },
  };

  let reviseFeedback = '';
  let showRevise = false;

  // 内联编辑
  let editingNum = -1;
  let editTitle = '';
  let editOutline = '';

  // 导入续写
  let showImport = false;
  let importContent = '';
  let continuationCount = 5;

  // 手动创建大纲
  let showManual = false;
  let manualTitle = '';
  let manualSynopsis = '';
  let manualCorePrompt = '';
  let manualChapters = [{ title: '', outline: '' }];

  // 添加新章节
  let newChapterTitle = '';
  let newChapterOutline = '';

  // 故事信息编辑
  let editingStory = false;
  let editStoryTitle = '';
  let editStorySynopsis = '';
  let editCorePrompt = '';

  async function startEditStory() {
    editStoryTitle = p?.title || '';
    editStorySynopsis = p?.story_synopsis || '';
    editCorePrompt = p?.core_prompt || '';
    editingStory = true;
  }

  async function saveStoryInfo() {
    try {
      // 发送完整配置，不是只发story子集
      const currentCfg = await api('GET', '/api/config');
      await api('PUT', '/api/config', {
        ...currentCfg,
        story: {
          ...(currentCfg.story || {}),
          title: editStoryTitle.trim(),
          story_synopsis: editStorySynopsis.trim(),
          core_prompt: editCorePrompt.trim(),
        },
      });
      progress.set(await api('GET', '/api/progress'));
      addToast('故事信息已更新', 'success');
      editingStory = false;
    } catch (e) { addToast(e.message, 'error'); }
  }

  async function generateOutline() {
    try {
      await api('POST', '/api/outline/generate');
      addToast($t('outline.toasts.outlineStarted'), 'info');
    } catch (e) { addToast(e.message, 'error'); }
  }

  async function confirmOutline() {
    showConfirm($t('outline.toasts.confirmAsk'), async () => {
      try {
        await api('POST', '/api/outline/confirm');
        progress.set(await api('GET', '/api/progress'));
        addToast($t('outline.toasts.outlineConfirmed'), 'success');
        window.location.hash = '#writing';
      } catch (e) { addToast(e.message, 'error'); }
    });
  }

  async function reviseOutline() {
    const fb = reviseFeedback.trim();
    if (!fb) { addToast($t('outline.toasts.reviseFeedbackRequired'), 'error'); return; }
    try {
      await api('POST', '/api/outline/revise', { feedback: fb });
      addToast($t('outline.toasts.reviseStarted'), 'info');
      reviseFeedback = '';
      showRevise = false;
    } catch (e) { addToast(e.message, 'error'); }
  }

  async function deleteOutline() {
    showConfirm($t('outline.toasts.deleteConfirm', { n: chapters.length }), async () => {
      try {
        await api('DELETE', '/api/outline');
        progress.set(await api('GET', '/api/progress'));
        addToast($t('outline.toasts.deleted'), 'success');
      } catch (e) { addToast(e.message, 'error'); }
    });
  }

  async function generateContinuation() {
    try {
      await api('POST', '/api/outline/generate-continuation', { chapter_count: Number(continuationCount) || 5 });
      addToast($t('outline.toasts.continuationStarted'), 'info');
    } catch (e) { addToast(e.message, 'error'); }
  }

  function startEdit(ch) {
    editingNum = ch.num;
    editTitle = ch.title;
    editOutline = ch.outline;
  }

  function cancelEdit() {
    editingNum = -1;
  }

  async function saveEdit() {
    if (!editTitle.trim() && !editOutline.trim()) { addToast('标题和大纲不能同时为空', 'error'); return; }
    try {
      await api('PUT', '/api/outline/' + editingNum, { title: editTitle.trim(), outline: editOutline.trim() });
      progress.set(await api('GET', '/api/progress'));
      addToast($t('outline.toasts.editSaved', { num: editingNum }), 'success');
      editingNum = -1;
    } catch (e) { addToast(e.message, 'error'); }
  }

  async function importExisting() {
    const content = importContent.trim();
    if (!content) { addToast($t('outline.toasts.importContentRequired'), 'error'); return; }
    try {
      await api('POST', '/api/continue/import', { content });
      addToast($t('outline.toasts.importStarted'), 'info');
    } catch (e) { addToast(e.message, 'error'); }
  }

  async function confirmImport() {
    if (!$continueAnalysis) return;
    try {
      await api('POST', '/api/continue/confirm', $continueAnalysis);
      progress.set(await api('GET', '/api/progress'));
      continueAnalysis.set(null);
      showImport = false;
      importContent = '';
      addToast($t('outline.toasts.importDone'), 'success');
    } catch (e) { addToast(e.message, 'error'); }
  }

  async function saveManualOutline() {
    const chapters = manualChapters.filter(c => c.title.trim() || c.outline.trim());
    if (chapters.length === 0) { addToast('至少需要添加一个章节', 'error'); return; }
    try {
      await api('POST', '/api/outline/manual', {
        title: manualTitle.trim(),
        synopsis: manualSynopsis.trim(),
        core_prompt: manualCorePrompt.trim(),
        chapters,
      });
      progress.set(await api('GET', '/api/progress'));
      addToast(`大纲已创建（${chapters.length} 章）`, 'success');
      showManual = false;
    } catch (e) { addToast(e.message, 'error'); }
  }

  async function uploadOutlineFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    manualSynopsis = text;
    addToast(`已加载文件：${file.name}（${text.length} 字）`, 'success');
    e.target.value = '';
  }

  function addManualChapter() {
    manualChapters = [...manualChapters, { title: '', outline: '' }];
  }

  function removeManualChapter(i) {
    manualChapters = manualChapters.filter((_, idx) => idx !== i);
  }

  async function addNewChapter() {
    if (!newChapterTitle.trim() && !newChapterOutline.trim()) {
      addToast('请输入章节标题或大纲', 'error');
      return;
    }
    try {
      await api('POST', '/api/outline/chapters', {
        title: newChapterTitle.trim(),
        outline: newChapterOutline.trim(),
      });
      progress.set(await api('GET', '/api/progress'));
      addToast('章节已添加', 'success');
      newChapterTitle = '';
      newChapterOutline = '';
    } catch (e) { addToast(e.message, 'error'); }
  }

  async function confirmCharacterSuggestions() {
    const selected = $outlineCharacterSuggestions.filter(s => s._selected !== false);
    if (selected.length === 0) {
      addToast($t('outline.charSuggestions.noneSelected'), 'error');
      return;
    }
    try {
      await api('POST', '/api/outline/characters/confirm', { characters: selected });
      settings.set(await api('GET', '/api/settings'));
      outlineCharacterSuggestions.set([]);
      outlineCharacterShowSuggestions.set(false);
      addToast($t('outline.charSuggestions.adopted', { n: selected.length }), 'success');
    } catch (e) { addToast(e.message, 'error'); }
  }

  function dismissCharacterSuggestions() {
    outlineCharacterSuggestions.set([]);
    outlineCharacterShowSuggestions.set(false);
  }

  async function parseOutline() {
    try {
      await api('POST', '/api/outline/parse');
      addToast('正在从大纲提取设定...', 'info');
    } catch (e) { addToast(e.message, 'error'); }
  }
</script>

<div class="space-y-3">
  {#if !hasOutline}
    <!-- 空状态 -->
    <div class="text-center py-14 text-base-content/50">
      <div class="text-5xl mb-3">📝</div>
      <p class="text-base mb-1">{$t('outline.empty.title')}</p>
      <p class="text-sm text-base-content/35 mb-6">{$t('outline.empty.hint')}</p>
      <div class="flex justify-center gap-2">
        <button class="btn btn-primary btn-sm" on:click={generateOutline} disabled={$taskRunning}>{$t('outline.btn.generate')}</button>
        <button class="btn btn-outline btn-sm" on:click={() => showManual = !showManual} disabled={$taskRunning}>手动创建</button>
        <button class="btn btn-ghost btn-sm" on:click={() => showImport = !showImport} disabled={$taskRunning}>{$t('outline.btn.import')}</button>
      </div>
    </div>

    {#if showImport}
      <div class="card bg-base-200 shadow-sm">
        <div class="card-body p-4 gap-2">
          <h3 class="card-title text-base">{$t('outline.import.title')}</h3>
          <p class="text-xs text-base-content/50">{$t('outline.import.hint')}</p>
          <textarea class="textarea w-full h-48 text-sm font-serif" bind:value={importContent} placeholder={$t('outline.import.placeholder')} disabled={$taskRunning}></textarea>
          <div class="flex justify-end gap-2">
            <button class="btn btn-ghost btn-xs" on:click={() => { showImport = false; importContent = ''; }}>{$t('common.cancel')}</button>
            <button class="btn btn-primary btn-xs" on:click={importExisting} disabled={$taskRunning || !importContent.trim()}>{$t('outline.import.start')}</button>
          </div>
        </div>
      </div>
    {/if}

    {#if showManual}
      <div class="card bg-base-200 shadow-sm border border-primary/30">
        <div class="card-body p-4 gap-3">
          <div class="flex items-center justify-between">
            <h3 class="card-title text-sm">手动创建大纲</h3>
            <button class="btn btn-ghost btn-xs" on:click={() => { showManual = false; manualChapters = [{ title: '', outline: '' }]; }}>取消</button>
          </div>
          <div class="space-y-2">
            <div>
              <span class="text-xs text-base-content/50 mb-0.5 block">小说标题</span>
              <input type="text" class="input input-sm w-full" bind:value={manualTitle} placeholder="例：破夜行" />
            </div>
            <div>
              <span class="text-xs text-base-content/50 mb-0.5 block">完整大纲（上传或用文件加载）</span>
              <textarea class="textarea textarea-sm w-full h-40 text-sm" bind:value={manualSynopsis} placeholder="粘贴你的完整大纲，或者通过下方「上传文件」按钮加载"></textarea>
            </div>
            <div>
              <span class="text-xs text-base-content/50 mb-0.5 block">创作指导（可选）</span>
              <textarea class="textarea textarea-sm w-full h-16 text-sm" bind:value={manualCorePrompt} placeholder="对AI写作的额外要求"></textarea>
            </div>
            <div>
              <span class="text-xs text-base-content/50 mb-1 block">章节列表</span>
              <div class="space-y-2">
                {#each manualChapters as ch, i}
                  <div class="flex gap-2 items-start bg-base-300 rounded-lg p-2">
                    <span class="text-sm font-bold text-base-content/40 mt-2 w-6 shrink-0">{i + 1}</span>
                    <div class="flex-1 space-y-1.5">
                      <input type="text" class="input input-xs w-full" bind:value={ch.title} placeholder="章节标题" />
                      <textarea class="textarea textarea-xs w-full h-14 text-xs" bind:value={ch.outline} placeholder="本章大纲（可选）"></textarea>
                    </div>
                    {#if manualChapters.length > 1}
                      <button class="btn btn-ghost btn-xs text-error mt-1" on:click={() => removeManualChapter(i)}>删除</button>
                    {/if}
                  </div>
                {/each}
              </div>
              <div class="flex gap-2 mt-2">
                <button class="btn btn-ghost btn-xs" on:click={addManualChapter}>+ 添加章节</button>
                <button class="btn btn-ghost btn-xs" on:click={() => document.getElementById('outlineFileInput')?.click()}>上传文件</button>
                <input id="outlineFileInput" type="file" accept=".txt,.md" class="hidden" on:change={uploadOutlineFile} />
                <button class="btn btn-success btn-xs ml-auto" on:click={saveManualOutline} disabled={$taskRunning}>保存大纲</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    {/if}

    {#if $continueAnalysis}
      <div class="card bg-base-200 shadow-sm border border-primary/30">
        <div class="card-body p-4 gap-2">
          <h3 class="card-title text-base">{$t('outline.analysis.title')}</h3>
          <div class="grid grid-cols-2 gap-2">
            <div>
              <span class="text-xs text-base-content/50 mb-0.5 block">{$t('outline.analysis.fields.title')}</span>
              <input type="text" class="input input-sm w-full" bind:value={$continueAnalysis.title} disabled={$taskRunning} />
            </div>
            <div>
              <span class="text-xs text-base-content/50 mb-0.5 block">{$t('outline.analysis.fields.type')}</span>
              <input type="text" class="input input-sm w-full" bind:value={$continueAnalysis.story_type} disabled={$taskRunning} />
            </div>
          </div>
          <div>
            <span class="text-xs text-base-content/50 mb-0.5 block">{$t('outline.analysis.fields.synopsis')}</span>
            <textarea class="textarea textarea-sm w-full h-20 text-sm" bind:value={$continueAnalysis.story_synopsis} disabled={$taskRunning}></textarea>
          </div>
          <div>
            <span class="text-xs text-base-content/50 mb-0.5 block">{$t('outline.analysis.fields.style')}</span>
            <textarea class="textarea textarea-sm w-full h-16 text-sm" bind:value={$continueAnalysis.writing_style} disabled={$taskRunning}></textarea>
          </div>
          <div>
            <span class="text-xs text-base-content/50 mb-0.5 block">{$t('outline.analysis.fields.pov')}</span>
            <textarea class="textarea textarea-sm w-full h-16 text-sm" bind:value={$continueAnalysis.writing_pov} disabled={$taskRunning}></textarea>
          </div>
          <div class="text-xs text-base-content/50">{$t('outline.analysis.detected', { n: $continueAnalysis.chapters?.length || 0 })}</div>
          <div class="max-h-48 overflow-y-auto space-y-1">
            {#each ($continueAnalysis.chapters || []) as ch}
              <div class="bg-base-300 rounded p-2 text-xs">
                <span class="font-medium">{$t('outline.analysis.chapter', { num: ch.num, title: ch.title })}</span>
                <span class="text-base-content/50">{ch.outline || ch.summary || ''}</span>
              </div>
            {/each}
          </div>
          <div class="flex justify-end gap-2">
            <button class="btn btn-ghost btn-xs" on:click={() => continueAnalysis.set(null)}>{$t('outline.analysis.abandon')}</button>
            <button class="btn btn-success btn-xs" on:click={confirmImport} disabled={$taskRunning}>{$t('outline.analysis.confirm')}</button>
          </div>
        </div>
      </div>
    {/if}
  {:else}
    <ConfigChangePanel />

    {#if $outlineCharacterShowSuggestions && $outlineCharacterSuggestions.length > 0}
      <div class="card bg-base-200 border border-primary/30 shadow-sm">
        <div class="card-body py-4 gap-3">
          <h3 class="font-semibold">{$t('outline.charSuggestions.title', { n: $outlineCharacterSuggestions.length })}</h3>
          <p class="text-sm text-base-content/60">{$t('outline.charSuggestions.hint')}</p>
          <div class="space-y-2 max-h-72 overflow-y-auto">
            {#each $outlineCharacterSuggestions as s}
              <label class="flex gap-3 p-3 rounded-lg bg-base-300/50 cursor-pointer">
                <input type="checkbox" class="checkbox checkbox-sm mt-1" bind:checked={s._selected} />
                <div class="min-w-0 flex-1">
                  <div class="font-medium">{s.name}</div>
                  {#if s.description}
                    <div class="text-sm text-base-content/70 mt-1">{s.description}</div>
                  {/if}
                  <div class="text-xs text-base-content/50 mt-1">
                    {$t('outline.charSuggestions.line', { chapter: s.chapter_num, role: s.role || $t('outline.charSuggestions.noRole') })}
                  </div>
                </div>
              </label>
            {/each}
          </div>
          <div class="flex gap-2">
            <button class="btn btn-primary btn-sm" disabled={$taskRunning} on:click={confirmCharacterSuggestions}>{$t('outline.charSuggestions.adopt')}</button>
            <button class="btn btn-ghost btn-sm" on:click={dismissCharacterSuggestions}>{$t('outline.charSuggestions.dismiss')}</button>
          </div>
        </div>
      </div>
    {/if}

    <!-- 操作栏 -->
    <div class="card bg-base-200 shadow-sm">
      <div class="card-body p-4 gap-2">
        <div class="flex items-center gap-2 flex-wrap">
          <h3 class="text-base font-semibold flex-1 min-w-0 truncate">📖 {displayTitle || $t('common.untitled')}</h3>
          <button class="btn btn-ghost btn-xs" on:click={startEditStory} disabled={editingStory}>编辑信息</button>
          {#if inOutlinePhase}
            <button class="btn btn-success btn-xs" on:click={confirmOutline} disabled={$taskRunning || chapters.length === 0}>{$t('outline.btn.confirm')}</button>
          {/if}
          {#if displaySynopsis}
            <button class="btn btn-ghost btn-xs" on:click={parseOutline} disabled={$taskRunning}>解析到接口</button>
          {/if}
          <button class="btn btn-ghost btn-xs" on:click={() => showRevise = !showRevise} disabled={$taskRunning}>{$t('outline.btn.revise')}</button>
          {#if hasAccepted}
            <div class="join">
              <input type="number" min="1" max="50" class="input input-xs join-item w-14" bind:value={continuationCount} disabled={$taskRunning} />
              <button class="btn btn-primary btn-xs join-item" on:click={generateContinuation} disabled={$taskRunning}>{$t('outline.btn.continuation')}</button>
            </div>
          {:else if inOutlinePhase}
            <button class="btn btn-ghost btn-xs" on:click={generateOutline} disabled={$taskRunning}>{$t('outline.btn.regenerate')}</button>
          {/if}
          {#if $taskRunning}
            <button class="btn btn-error btn-xs" on:click={() => api('POST', '/api/task/stop').catch(() => {})}>停止</button>
          {/if}
          {#if !hasAccepted}
            <button class="btn btn-ghost btn-xs text-error" on:click={deleteOutline} disabled={$taskRunning}>{$t('outline.btn.deleteOutline')}</button>
          {/if}
        </div>

        {#if showRevise}
          <div class="bg-base-300 rounded-lg p-3 space-y-2">
            <textarea class="textarea textarea-sm w-full h-20 text-sm" bind:value={reviseFeedback} placeholder={$t('outline.revise.placeholder')} disabled={$taskRunning}></textarea>
            <div class="flex justify-between items-center">
              <span class="text-xs text-base-content/40">{$t('outline.revise.hint')}</span>
              <div class="flex gap-2">
                <button class="btn btn-ghost btn-xs" on:click={() => { showRevise = false; reviseFeedback = ''; }}>{$t('common.cancel')}</button>
                <button class="btn btn-primary btn-xs" on:click={reviseOutline} disabled={$taskRunning || !reviseFeedback.trim()}>{$t('outline.revise.submit')}</button>
              </div>
            </div>
          </div>
        {/if}

        {#if editingStory}
          <div class="space-y-2 bg-base-300 rounded-lg p-3">
            <div>
              <span class="text-xs text-base-content/50 mb-0.5 block">小说标题</span>
              <input type="text" class="input input-sm w-full" bind:value={editStoryTitle} />
            </div>
            <div>
              <span class="text-xs text-base-content/50 mb-0.5 block">创作指导</span>
              <textarea class="textarea textarea-sm w-full h-16 text-sm" bind:value={editCorePrompt}></textarea>
            </div>
            <div>
              <span class="text-xs text-base-content/50 mb-0.5 block">故事简介 / 大纲</span>
              <textarea class="textarea textarea-sm w-full h-32 text-sm font-serif" bind:value={editStorySynopsis}></textarea>
            </div>
            <div class="flex justify-end gap-2">
              <button class="btn btn-ghost btn-xs" on:click={() => editingStory = false}>取消</button>
              <button class="btn btn-success btn-xs" on:click={saveStoryInfo} disabled={$taskRunning}>保存</button>
            </div>
          </div>
        {:else}
          {#if p.core_prompt}
            <div>
              <span class="text-xs text-base-content/50">{$t('outline.corePrompt')}</span>
              <div class="bg-base-300 rounded p-2 text-sm mt-0.5 max-h-24 overflow-y-auto">{p.core_prompt}</div>
            </div>
          {/if}
          {#if displaySynopsis}
            <div>
              <span class="text-xs text-base-content/50">{$t('outline.synopsis')}</span>
              <div class="bg-base-300 rounded p-2 text-sm mt-0.5 max-h-32 overflow-y-auto">{displaySynopsis}</div>
            </div>
          {/if}
        {/if}
      </div>
    </div>

    <!-- 章节大纲列表 -->
    <div class="card bg-base-200 shadow-sm">
      <div class="card-body p-4 gap-2">
        <div class="flex items-center justify-between">
          <h4 class="text-sm font-semibold text-base-content/60">{$t('outline.chapterList')} <span class="font-normal text-base-content/35">{$t('outline.chapterList.summary', { total: chapters.length, suffix: pendingCount ? $t('outline.chapterList.pendingSuffix', { n: pendingCount }) : '' })}</span></h4>
          <span class="text-xs text-base-content/35">{$t('outline.chapterList.editHint')}</span>
        </div>
        <div class="space-y-1.5">
          {#each chapters as ch (ch.num)}
            {#if editingNum === ch.num}
              <div class="bg-base-300 rounded-lg p-3 space-y-2 ring-1 ring-primary/50">
                <div class="flex items-center gap-2">
                  <span class="text-sm font-bold text-base-content/50 shrink-0">{$t('outline.chapter.chapterLabel', { num: ch.num })}</span>
                  <input type="text" class="input input-sm flex-1" bind:value={editTitle} placeholder={$t('outline.chapter.titlePlaceholder')} disabled={$taskRunning} />
                </div>
                <textarea class="textarea textarea-sm w-full h-24 text-sm" bind:value={editOutline} placeholder={$t('outline.chapter.outlinePlaceholder')} disabled={$taskRunning}></textarea>
                <div class="flex justify-end gap-2">
                  <button class="btn btn-ghost btn-xs" on:click={cancelEdit}>{$t('common.cancel')}</button>
                  <button class="btn btn-success btn-xs" on:click={saveEdit} disabled={$taskRunning}>{$t('common.save')}</button>
                </div>
              </div>
            {:else}
              <!-- svelte-ignore a11y-click-events-have-key-events -->
              <!-- svelte-ignore a11y-no-static-element-interactions -->
              <div
                class="bg-base-300 rounded-lg p-2.5 group {ch.status !== 'writing' && !$taskRunning ? 'cursor-pointer hover:ring-1 hover:ring-primary/40' : ''} transition-shadow"
                on:click={() => ch.status !== 'writing' && !$taskRunning && startEdit(ch)}
              >
                <div class="flex items-center gap-2">
                  <span class="text-sm font-bold text-base-content/40 w-12 shrink-0">{ch.num}</span>
                  <span class="text-sm font-medium flex-1 min-w-0 truncate">{ch.title}</span>
                  <span class="badge badge-xs {statusMeta[ch.status]?.cls || 'badge-ghost'}">{statusMeta[ch.status]?.label || ch.status}</span>
                  {#if ch.status === 'pending'}
                    <span class="text-xs text-primary opacity-0 group-hover:opacity-100 transition-opacity shrink-0">{$t('outline.chapter.editTag')}</span>
                  {/if}
                </div>
                <p class="text-xs text-base-content/50 mt-1 ml-14 line-clamp-2">{ch.outline}</p>
              </div>
            {/if}
          {/each}
        </div>

        <!-- 添加章节 -->
        <div class="flex items-center gap-2 mt-2 p-3 bg-base-300/40 rounded-lg">
          <input type="text" class="input input-xs flex-1" bind:value={newChapterTitle} placeholder="章节标题" />
          <input type="text" class="input input-xs flex-[2]" bind:value={newChapterOutline} placeholder="章节大纲（可选）" />
          <button class="btn btn-primary btn-xs" on:click={addNewChapter} disabled={$taskRunning}>添加</button>
        </div>

        {#if $streamingChapterIdx >= 0 && $streamingContent}
          <div class="bg-base-300 rounded p-3 mt-1 text-sm max-h-48 overflow-y-auto chapter-content">
            <div class="text-xs text-base-content/40 mb-1 flex items-center gap-1">
              <span class="loading loading-dots loading-xs"></span> {$t('outline.streamHint')}
            </div>
            {$streamingContent}
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>
