<script lang="ts">
  import { page } from '$app/state';
  import { browser } from '$app/environment';
  import { untrack } from 'svelte';
  import { PUBLIC_BACKEND_URL } from '$env/static/public';
  import { SvelteSet } from 'svelte/reactivity';
  import SeasonInfo from '$lib/components/SeasonInfo/SeasonInfo.svelte';
  import ColorTable from '$lib/components/ColorTable/ColorTable.svelte';
  import SpoilerText from '$lib/components/SpoilerText/SpoilerText.svelte';
  import DownloadIcon from "@lucide/svelte/icons/download";
  import PauseIcon from "@lucide/svelte/icons/pause";
  import PlayIcon from "@lucide/svelte/icons/play";
  import Trash2Icon from "@lucide/svelte/icons/trash-2";
  import type { PageProps } from './$types';

  let { data }: PageProps = $props();

  // Local mutable copy — SSE patches status in place without server re-fetches.
  // untrack: intentionally capture data once; component remounts on navigation with fresh data.
  let episodes = $state(untrack(() => data.episodes.map(e => ({ ...e }))));

  const highlightId = $derived(page.url.searchParams.get("id") ?? undefined);

  let loadingIds = new SvelteSet<number>();
  let error = $state<string | null>(null);

  // Maps raw SSE status strings to the display strings the API already uses
  const SSE_STATUS_MAP: Record<string, string> = {
    downloading: 'Downloading',
    pending: 'Pending',
    paused: 'Paused',
    hardlink: 'Hardlinked',
    copy: 'Copied',
    error: 'Error',
    removed: 'Not Downloaded',
  };

  // Only cares about status changes — no progress bars on this page
  $effect(() => {
    if (!browser) return;
    const source = new EventSource(`${PUBLIC_BACKEND_URL}/events/downloads`);
    source.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data);
        if (event.ep_id === undefined) return;
        if (event.type !== 'episode_download_started' && event.type !== 'episode_status_changed') return;
        const ep = episodes.find(ep => ep.ep_id === event.ep_id);
        if (ep) ep.status = SSE_STATUS_MAP[event.status] ?? event.status;
      } catch {}
    };
    return () => source.close();
  });

  async function callApi(episodeId: number | null, path: string, method: string) {
    if (episodeId !== null) loadingIds.add(episodeId);
    error = null;
    try {
      const res = await fetch(`${PUBLIC_BACKEND_URL}${path}`, { method });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        error = body.detail ?? 'Request failed';
      } else if (res.status === 204) {
        // DELETE — episode(s) no longer tracked
        if (episodeId !== null) {
          const ep = episodes.find(e => e.ep_id === episodeId);
          if (ep) ep.status = 'Not Downloaded';
        } else {
          for (const ep of episodes) ep.status = 'Not Downloaded';
        }
      } else {
        const updated = await res.json();
        if (Array.isArray(updated)) {
          for (const u of updated) {
            const ep = episodes.find(e => e.ep_id === u.ep_id);
            if (ep && u.status) ep.status = u.status;
          }
        } else {
          const ep = episodes.find(e => e.ep_id === episodeId);
          if (ep && updated.status) ep.status = updated.status;
        }
      }
    } catch {
      error = 'Could not reach the server';
    } finally {
      if (episodeId !== null) loadingIds.delete(episodeId);
    }
  }

  const seasonNum = data.season.num;

  const DOWNLOADABLE = new Set(['Not Downloaded', 'Error']);
  const PAUSABLE     = new Set(['Downloading', 'Pending']);
  const RESUMABLE    = new Set(['Paused']);
  const DELETABLE    = new Set(['Pending', 'Downloading', 'Paused', 'Hardlinked', 'Copied', 'Error']);
</script>

<div class="flex flex-col gap-6">
  <SeasonInfo num={data.season.num.toString()} title={data.season.title} image={data.season.image} description={data.season.description}>
    {#snippet actions()}
      <button class="btn preset-filled-primary-500 rounded-xl text-sm" onclick={() => callApi(null, `/season/${seasonNum}/download`, 'POST')}><DownloadIcon size={18}/><span>Download All</span></button>
      <button class="btn preset-tonal-warning rounded-xl text-sm" onclick={() => callApi(null, `/season/${seasonNum}/pause`, 'POST')}><PauseIcon size={18}/><span>Pause All</span></button>
      <button class="btn preset-tonal-success rounded-xl text-sm" onclick={() => callApi(null, `/season/${seasonNum}/resume`, 'POST')}><PlayIcon size={18}/><span>Resume All</span></button>
      <button class="btn preset-tonal-error rounded-xl text-sm" onclick={() => callApi(null, `/season/${seasonNum}`, 'DELETE')}><Trash2Icon size={18}/><span>Delete All</span></button>
    {/snippet}
  </SeasonInfo>
  {#if error}
    <div class="preset-tonal-error rounded p-3 text-sm">{error}</div>
  {/if}
  <ColorTable data={episodes} searchBox={true} searchableFields={['number', 'title']} highlightId={highlightId} idKey="ep_id">
    {#snippet header()}
      <th>Season</th>
      <th>Episode</th>
      <th>Name</th>
      <th>Duration</th>
      <th>Status</th>
      <th>Actions</th>
    {/snippet}
    {#snippet row(episode)}
      {@const isLoading = loadingIds.has(episode.ep_id)}
      <td>{episode.season}</td>
      <td>{episode.number}</td>
      <td><SpoilerText>{episode.title}</SpoilerText></td>
      <td>{episode.duration}</td>
      <td>{#if episode.status !== 'Not Downloaded'}<a class="text-blue-500 hover:underline" href={`/downloads?tab=episodes&id=${episode.ep_id}`}>{episode.status}</a>{:else}{episode.status}{/if}</td>
      <td>
        <button class="btn-icon" disabled={isLoading || !DOWNLOADABLE.has(episode.status)} onclick={() => callApi(episode.ep_id, `/episode/${episode.ep_id}/download`, 'POST')}><DownloadIcon /></button>
        {#if RESUMABLE.has(episode.status)}
          <button class="btn-icon" disabled={isLoading} onclick={() => callApi(episode.ep_id, `/episode/${episode.ep_id}/resume`, 'POST')}><PlayIcon /></button>
        {:else}
          <button class="btn-icon" disabled={isLoading || !PAUSABLE.has(episode.status)} onclick={() => callApi(episode.ep_id, `/episode/${episode.ep_id}/pause`, 'POST')}><PauseIcon /></button>
        {/if}
        <button class="btn-icon" disabled={isLoading || !DELETABLE.has(episode.status)} onclick={() => callApi(episode.ep_id, `/episode/${episode.ep_id}`, 'DELETE')}><Trash2Icon /></button>
      </td>
    {/snippet}
  </ColorTable>
</div>
