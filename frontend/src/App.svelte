<script>
  import { currentPage } from './lib/router.js';
  import { progress, taskRunning, contextPage, toastStore, currentProject, projectLanguage } from './lib/stores.js';
  import { connectSSE } from './lib/sse.js';
  import { api } from './lib/api.js';
  import { onMount } from 'svelte';
  import { t, uiLocale, setLocale } from './lib/i18n/index.js';
  import TaskTokenBadge from './components/TaskTokenBadge.svelte';
  import Projects from './pages/Projects.svelte';
  import Config from './pages/Config.svelte';
  import Outline from './pages/Outline.svelte';
  import Writing from './pages/Writing.svelte';
  import Relations from './pages/Relations.svelte';
  import Skills from './pages/Skills.svelte';
  import Foreshadows from './pages/Foreshadows.svelte';
  import Memory from './pages/Memory.svelte';
  import ChatPanel from './components/ChatPanel.svelte';
  import ConfirmModal from './components/ConfirmModal.svelte';

  let chatPanel;

  let mem0Online = false;
  let mem0Total = 0;
  let checkMem0Interval;
  let appVersion = '';
  let latestVersion = '';
  let hasUpdate = false;

  $: phase = $progress
  $: $contextPage = $currentPage;

  async function checkMem0() {
    try {
      const stats = await api('GET', '/api/memories/mem0/stats');
      mem0Online = stats?.running || false;
      mem0Total = stats?.total || 0;
    } catch (e) { mem0Online = false; }
  }

  onMount(async () => {
    connectSSE();
    // Fetch app version
    try {
      const ver = await api('GET', '/api/version');
      appVersion = ver.version || 'dev';
    } catch (e) {}
    // Check for updates (skip for dev builds)
    if (appVersion && appVersion !== 'dev') {
      try {
        const resp = await fetch('https://api.github.com/repos/Nigh/show-me-the-story/releases/latest');
        if (resp.ok) {
          const data = await resp.json();
          latestVersion = data.tag_name || '';
          if (latestVersion && latestVersion !== appVersion) {
            hasUpdate = true;
          }
        }
      } catch (e) {}
    }
    // Check if a project is already selected
    try {
      const cur = await api('GET', '/api/projects/current');
      if (cur.name) {
        currentProject.set(cur.name);
        if (cur.language) {
          projectLanguage.set(cur.language);
          setLocale(cur.language);
        }
        try { const p = await api('GET', '/api/progress'); progress.set(p); } catch (e) {}
      }
    } catch (e) {}
    // Mem0 status check
    checkMem0();
    setInterval(checkMem0, 60000);
  });

  $: phase = $progress
    ? ($progress.phase === 'outline' ? $t('app.phase.outline')
        : $progress.phase === 'writing' ? $t('app.phase.writing')
        : $progress.phase)
    : $t('app.phase.unstarted');
  $: chapterStats = (() => {
    const chs = $progress?.chapters || [];
    if (chs.length === 0) return '';
    const accepted = chs.filter(c => c.status === 'accepted').length;
    return $t('app.chapters.count', { accepted, total: chs.length });
  })();

  async function sendToChat(text) {
    if (chatPanel) await chatPanel.sendMessageToChat(text);
  }

  function backToProjects() {
    currentProject.set(null);
  }

  function toggleLocale() {
    setLocale($uiLocale === 'en' ? 'zh' : 'en');
  }
</script>

<div class="flex flex-col min-h-screen h-full bg-base-300 text-base-content overflow-hidden" style="min-height:100dvh">
  <!-- Header -->
  <header class="navbar bg-base-200 border-b border-base-content/10 px-6 min-h-[46px] shrink-0 gap-4">
    <span class="text-lg font-semibold">{$t('app.title')}</span>
    {#if appVersion}
      <span class="badge badge-xs badge-ghost font-mono">{appVersion}</span>
    {/if}
    {#if hasUpdate}
      <a href={latestReleaseURL} target="_blank" rel="noopener" class="badge badge-xs badge-warning gap-0.5 no-underline">
        {$t('app.newVersion')}
      </a>
    {/if}
    {#if $currentProject}
      <span class="badge badge-sm badge-outline">{$currentProject}</span>
      <span class="badge badge-sm badge-accent uppercase" title={$projectLanguage === 'en' ? 'English' : '中文'}>
        {$projectLanguage === 'en' ? 'EN' : 'ZH'}
      </span>
      <button
        class="btn btn-ghost btn-xs gap-1"
        on:click={backToProjects}
        disabled={$taskRunning}
        title={$taskRunning ? $t('app.switchProject.disabled') : $t('app.switchProject.tooltip')}
      >
        {$t('app.switchProject')}
      </button>
      <span class="badge badge-sm" class:badge-primary={$progress}>{phase}</span>
      {#if chapterStats}
        <span class="badge badge-sm badge-ghost">{chapterStats}</span>
      {/if}
      <!-- Mem0 status -->
      <span class="badge badge-xs" class:badge-success={mem0Online} class:badge-error={!mem0Online}>
        M{mem0Online ? `:${mem0Total}` : '✕'}
      </span>
      {#if $taskRunning}
        <span class="badge badge-sm badge-warning gap-1">
          <span class="loading loading-spinner loading-xs"></span>
          {$t('app.aiThinking')}
          <TaskTokenBadge className="badge badge-xs badge-warning font-mono border-0" />
        </span>
      {/if}
    {/if}
    <span class="flex-1"></span>
    <button
      class="btn btn-ghost btn-xs gap-1"
      on:click={toggleLocale}
      title={$t('app.uiLang.label')}
    >
      {$uiLocale === 'en' ? $t('app.uiLang.en') : $t('app.uiLang.zh')}
    </button>
  </header>

  {#if !$currentProject}
    <!-- Project selection -->
    <main class="flex-1 overflow-y-auto p-6">
      <Projects />
    </main>
  {:else}
    <div class="flex flex-1 overflow-hidden">
      <!-- Left: vertical nav -->
      <nav class="flex flex-col w-14 lg:w-44 shrink-0 bg-base-200 border-r border-base-content/10 py-2 px-1 lg:py-3 lg:px-2 gap-0.5">
        {#each [
          ['config', 'nav.config', `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`],
          ['outline', 'nav.outline', `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>`],
          ['writing', 'nav.writing', `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>`],
          ['foreshadows', 'nav.foreshadows', `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>`],
          ['memory', 'nav.memory', `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>`],
          ['relations', 'nav.relations', `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><circle cx="19" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><path d="M13.5 10.5 17 7"/><path d="M7 17l2.5-2.5"/></svg>`],
          ['skills', 'nav.skills', `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="8" height="8" rx="2"/><rect x="14" y="2" width="8" height="8" rx="2"/><rect x="2" y="14" width="8" height="8" rx="2"/><rect x="14" y="14" width="8" height="8" rx="2"/></svg>`]
        ] as [page, labelKey, svg]}
          <button
            class="btn btn-sm justify-start w-full gap-1.5 lg:gap-2.5 px-1 lg:px-3 text-xs lg:text-sm nav-btn {$currentPage === page ? 'btn-primary font-medium' : 'btn-ghost'}"
            on:click={() => window.location.hash = '#' + page}
            title={$t(labelKey)}
          >
            <span class="shrink-0 mx-auto lg:mx-0">{@html svg}</span><span class="hidden lg:inline">{$t(labelKey)}</span>
          </button>
        {/each}
      </nav>

      <!-- Center: page content -->
      <main class="flex-1 min-w-0 overflow-y-auto p-2 sm:p-4 border-r border-base-content/10">
        {#if $currentPage === 'config'}
          <Config {sendToChat} />
        {:else if $currentPage === 'outline'}
          <Outline {sendToChat} />
        {:else if $currentPage === 'writing'}
          <Writing {sendToChat} />
        {:else if $currentPage === 'foreshadows'}
          <Foreshadows />
        {:else if $currentPage === 'memory'}
          <Memory />
        {:else if $currentPage === 'relations'}
          <Relations />
        {:else if $currentPage === 'skills'}
          <Skills />
        {/if}
      </main>

      <!-- Right: Chat Panel -->
      <div class="w-48 sm:w-56 md:w-64 lg:w-80 xl:flex-1 min-w-0 bg-base-200 overflow-hidden">
        <ChatPanel bind:this={chatPanel} contextPage={$currentPage} />
      </div>
    </div>
  {/if}

  <!-- Toasts -->
  <div class="fixed top-5 right-5 z-50 flex flex-col gap-2">
    {#each $toastStore as t (t.id)}
      <div class="alert alert-sm {t.type === 'success' ? 'alert-success' : t.type === 'error' ? 'alert-error' : 'alert-info'} toast-enter shadow-lg max-w-sm">
        <span>{t.msg}</span>
      </div>
    {/each}
  </div>

  <ConfirmModal />
</div>
