<script lang="ts">
  import { page } from "$app/state";
  import { invalidateAll } from "$app/navigation";
  import { browser } from '$app/environment';
  import { untrack } from 'svelte';
  import { PUBLIC_BACKEND_URL } from '$env/static/public';
  import { SvelteSet } from 'svelte/reactivity';
  import { Tabs } from "@skeletonlabs/skeleton-svelte";
  import ColorTable from "$lib/components/ColorTable/ColorTable.svelte";
  import PauseIcon from "@lucide/svelte/icons/pause";
  import PlayIcon from "@lucide/svelte/icons/play";
  import Trash2Icon from "@lucide/svelte/icons/trash-2";
  import ScanSearchIcon from "@lucide/svelte/icons/scan-search";
  import SpoilerText from "$lib/components/SpoilerText/SpoilerText.svelte";
  import DownloadProgress from "$lib/components/DownloadProgress/DownloadProgress.svelte";
  import type { PageProps } from "./$types";

  let { data }: PageProps = $props();

  type ScanEpisodeInfo = { ep_id: number; title: string; season: number; status: string | null; error: string | null };
  type ScanResult = { found: ScanEpisodeInfo[]; already_tracked: ScanEpisodeInfo[]; errors: ScanEpisodeInfo[] };

  // Local mutable copies — SSE updates progress/status in place
  let episodes = $state(untrack(() => data.episodes.map(e => ({ ...e }))));
  let torrents = $state(untrack(() => data.torrents.map(t => ({ ...t }))));

  // Sync when server data changes — only triggered when invalidateAll() is called
  // (on episode_download_started / scan_complete, to pull in new rows)
  $effect(() => { episodes = data.episodes.map(e => ({ ...e })); });
  $effect(() => { torrents = data.torrents.map(t => ({ ...t })); });

  const highlightId = $derived(page.url.searchParams.get("id") ?? undefined);

  let episodeLoadingIds = new SvelteSet<number | string>();
  let torrentLoadingIds = new SvelteSet<number | string>();
  let error = $state<string | null>(null);
  let scanResult = $state<ScanResult | null>(null);

  const scanning = $derived(episodeLoadingIds.has('scan'));

  const SSE_STATUS_MAP: Record<string, string> = {
    downloading: 'Downloading',
    pending: 'Pending',
    paused: 'Paused',
    hardlink: 'Hardlinked',
    copy: 'Copied',
    error: 'Error',
    completed: 'Completed',
    imported: 'Imported',
  };

  $effect(() => {
    if (!browser) return;
    const source = new EventSource(`${PUBLIC_BACKEND_URL}/events/downloads`);
    source.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data);
        if (event.type === 'download_progress') {
          if (event.subject === 'episode') {
            const ep = episodes.find(ep => ep.ep_id === event.ep_id);
            if (ep) ep.progress = event.progress;
          } else if (event.subject === 'torrent') {
            const t = torrents.find(t => t.infohash === event.infohash);
            if (t) t.progress = event.progress;
          }
        } else if (event.type === 'episode_status_changed') {
          if (event.ep_id !== undefined) {
            if (event.status === 'removed') {
              episodes = episodes.filter(ep => ep.ep_id !== event.ep_id);
            } else {
              const ep = episodes.find(ep => ep.ep_id === event.ep_id);
              if (ep) ep.status = SSE_STATUS_MAP[event.status] ?? event.status;
            }
          } else if (event.infohash !== undefined) {
            if (event.status === 'removed') {
              torrents = torrents.filter(t => t.infohash !== event.infohash);
              episodes = episodes.filter(ep => ep.torrent_infohash !== event.infohash);
            } else {
              const t = torrents.find(t => t.infohash === event.infohash);
              if (t) t.status = SSE_STATUS_MAP[event.status] ?? event.status;
            }
          }
        } else if (event.type === 'episode_download_started' || event.type === 'scan_complete') {
          invalidateAll();
        }
      } catch {}
    };
    return () => source.close();
  });

  async function callApi(
    loadingIds: SvelteSet<number | string>,
    id: number | string,
    path: string,
    method: string,
    onSuccess?: (res: Response) => Promise<void>,
  ) {
    loadingIds.add(id);
    error = null;
    try {
      const res = await fetch(`${PUBLIC_BACKEND_URL}${path}`, { method });
      if (res.ok) {
        if (onSuccess) await onSuccess(res);
      } else {
        const body = await res.json().catch(() => ({}));
        error = body.detail ?? 'Request failed';
      }
    } catch {
      error = 'Could not reach the server';
    } finally {
      loadingIds.delete(id);
    }
  }

  const EP_PAUSABLE  = new Set(['Downloading', 'Pending']);
  const EP_RESUMABLE = new Set(['Paused']);
  const EP_DELETABLE = new Set(['Pending', 'Downloading', 'Paused', 'Hardlinked', 'Copied', 'Error', 'Imported']);

  const T_PAUSABLE  = new Set(['Downloading', 'Pending']);
  const T_RESUMABLE = new Set(['Paused']);
  const T_DELETABLE = new Set(['Pending', 'Downloading', 'Paused', 'Completed', 'Error']);
</script>

<div class="flex items-center justify-between -mt-2 mb-4">
  <h1 class="text-2xl font-bold">Downloads</h1>
  <button class="btn preset-tonal" disabled={scanning} onclick={() => callApi(episodeLoadingIds, 'scan', '/scan', 'POST', async (res) => {
    scanResult = await res.json();
    if (scanResult && scanResult.found.length > 0) await invalidateAll();
  })}>
    <ScanSearchIcon size={16} />
    {scanning ? 'Scanning…' : 'Scan for Existing Episodes'}
  </button>
</div>

{#if error}
  <div class="preset-tonal-error rounded p-3 text-sm mb-3">{error}</div>
{/if}
{#if scanResult}
  {@const foundCount = scanResult.found.length}
  {@const trackedCount = scanResult.already_tracked.length}
  {@const errorCount = scanResult.errors.length}
  <div class="preset-tonal-success rounded p-3 text-sm mb-3 flex items-center justify-between">
    <span>
      Scan complete:
      {foundCount} new episode{foundCount !== 1 ? 's' : ''} found
      {#if trackedCount > 0}&nbsp;· {trackedCount} already tracked{/if}
      {#if errorCount > 0}&nbsp;· {errorCount} error{errorCount !== 1 ? 's' : ''}{/if}
    </span>
    <button class="btn-icon btn-sm" onclick={() => scanResult = null}>✕</button>
  </div>
{/if}

{#key page.url.search}
<Tabs defaultValue={page.url.searchParams.get("tab") ?? "episodes"} onValueChange={(details) => history.replaceState(null, '', `?tab=${details.value}`)}>
  <Tabs.List>
    <Tabs.Trigger class="flex-1" value="episodes">Episodes</Tabs.Trigger>
    <Tabs.Trigger class="flex-1" value="torrents">Torrents</Tabs.Trigger>
    <Tabs.Indicator />
  </Tabs.List>
  <Tabs.Content value="episodes">
    <span class="mb-3 chip bg-black/10 dark:bg-white/20 hover:bg-black/20 dark:hover:bg-white/20">Note: Pausing/resuming an episode download will pause/resume the entire torrent, potentially affecting other episodes in the same torrent.</span>
    <ColorTable data={episodes} searchBox={true} searchableFields={['ep_id', 'title', 'status', 'torrent_name']} highlightId={highlightId} idKey="ep_id">
      {#snippet header()}
        <th>Episode ID</th>
        <th>Name</th>
        <th>Extended</th>
        <th>Status</th>
        <th>Download Progress</th>
        <th>Torrent</th>
        <th>Actions</th>
      {/snippet}
      {#snippet row(item)}
        {@const isLoading = episodeLoadingIds.has(item.ep_id)}
        <td><a class="text-blue-500 hover:underline" href={`/season/${item.season}?id=${item.ep_id}`}>{item.ep_id}</a></td>
        <td><a class="text-blue-500 hover:underline" href={`/season/${item.season}?id=${item.ep_id}`}><SpoilerText>{item.title}</SpoilerText></a></td>
        <td>{item.extended ? 'Yes' : 'No'}</td>
        <td>{item.status}</td>
        <td><DownloadProgress value={item.progress} status={item.status} /></td>
        <td>
          {#if item.torrent_infohash}
            <a class="text-blue-500 hover:underline" href={`/downloads?tab=torrents&id=${item.torrent_infohash}`}>{item.torrent_name}</a>
          {:else}
            —
          {/if}
        </td>
        <td>
          {#if EP_RESUMABLE.has(item.status)}
            <button class="btn-icon" disabled={isLoading} onclick={() => callApi(episodeLoadingIds, item.ep_id, `/episode/${item.ep_id}/resume`, 'POST')}><PlayIcon /></button>
          {:else}
            <button class="btn-icon" disabled={isLoading || !EP_PAUSABLE.has(item.status)} onclick={() => callApi(episodeLoadingIds, item.ep_id, `/episode/${item.ep_id}/pause`, 'POST')}><PauseIcon /></button>
          {/if}
          <button class="btn-icon" disabled={isLoading || !EP_DELETABLE.has(item.status)} onclick={() => callApi(episodeLoadingIds, item.ep_id, `/episode/${item.ep_id}`, 'DELETE')}><Trash2Icon /></button>
        </td>
      {/snippet}
    </ColorTable>
  </Tabs.Content>
  <Tabs.Content value="torrents">
    <ColorTable data={torrents} searchBox={true} searchableFields={['name', 'status', 'ep_ids']} highlightId={highlightId} idKey="infohash">
      {#snippet header()}
        <th>Name</th>
        <th>Status</th>
        <th>Download Progress</th>
        <th>Episodes</th>
        <th>Actions</th>
      {/snippet}
      {#snippet row(item)}
        {@const isLoading = torrentLoadingIds.has(item.infohash)}
        <td>{item.name}</td>
        <td>{item.status}</td>
        <td><DownloadProgress value={item.progress} status={item.status} /></td>
        <td>
          {#each item.ep_ids as ep_id, index (ep_id)}
            {#if index !== 0}&nbsp;{/if}
            <a class="text-blue-500 hover:underline" href={`/downloads?tab=episodes&id=${ep_id}`}>{ep_id}</a>
          {/each}
        </td>
        <td>
          {#if T_RESUMABLE.has(item.status)}
            <button class="btn-icon" disabled={isLoading} onclick={() => callApi(torrentLoadingIds, item.infohash, `/torrent/${item.infohash}/resume`, 'POST')}><PlayIcon /></button>
          {:else}
            <button class="btn-icon" disabled={isLoading || !T_PAUSABLE.has(item.status)} onclick={() => callApi(torrentLoadingIds, item.infohash, `/torrent/${item.infohash}/pause`, 'POST')}><PauseIcon /></button>
          {/if}
          <button class="btn-icon" disabled={isLoading || !T_DELETABLE.has(item.status)} onclick={() => callApi(torrentLoadingIds, item.infohash, `/torrent/${item.infohash}`, 'DELETE')}><Trash2Icon /></button>
        </td>
      {/snippet}
    </ColorTable>
  </Tabs.Content>
</Tabs>
{/key}
