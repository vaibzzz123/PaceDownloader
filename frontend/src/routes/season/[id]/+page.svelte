<script lang="ts">
  import { page } from '$app/state';
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

  let isDownloadRunning = $state(false);
</script>

<div class="flex flex-col gap-6">
  <SeasonInfo num={data.season.num.toString()} title={data.season.title} image={data.season.image} description={data.season.description} />
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
      <td>{episode.season}</td>
      <td>{episode.number}</td>
      <td><SpoilerText>{episode.title}</SpoilerText></td>
      <td>{episode.duration}</td>
      <td>{#if episode.status !== 'Not Downloaded'}<a class="text-blue-500 hover:underline" href={`/downloads?tab=episodes&id=${episode.ep_id}`}>{episode.status}</a>{:else}{episode.status}{/if}</td>
      <td>
        <button class="btn-icon" disabled={isDownloadRunning}><DownloadIcon /></button>
        <button class="btn-icon" onclick={() => isDownloadRunning = !isDownloadRunning}>{#if isDownloadRunning}<PauseIcon/>{:else}<PlayIcon/>{/if}</button>
        <button class="btn-icon"><Trash2Icon /></button>
      </td>
    {/snippet}
  </ColorTable>
</div>
