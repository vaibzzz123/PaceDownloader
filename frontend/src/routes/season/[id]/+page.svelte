<script lang="ts">
  import { page } from '$app/state';
  import { invalidateAll } from '$app/navigation';
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

  const highlightId = $derived(page.url.searchParams.get("id") ?? undefined);
  const episodes = $derived(data.episodes);

  let loadingIds = new SvelteSet<number>();
  let error = $state<string | null>(null);

  async function callApi(episodeId: number, path: string, method: string) {
    loadingIds.add(episodeId);
    error = null;
    try {
      const res = await fetch(`${PUBLIC_BACKEND_URL}${path}`, { method });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        error = body.detail ?? 'Request failed';
      } else {
        await invalidateAll();
      }
    } catch {
      error = 'Could not reach the server';
    } finally {
      loadingIds.delete(episodeId);
    }
  }

  const DOWNLOADABLE = new Set(['Not Downloaded', 'Error']);
  const PAUSABLE     = new Set(['Downloading', 'Pending']);
  const RESUMABLE    = new Set(['Paused']);
  const DELETABLE    = new Set(['Pending', 'Downloading', 'Paused', 'Hardlinked', 'Copied', 'Error']);
</script>

<div class="flex flex-col gap-6">
  <SeasonInfo num={data.season.num.toString()} title={data.season.title} image={data.season.image} description={data.season.description} />
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
