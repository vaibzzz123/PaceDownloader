<script lang="ts">
  import { page } from '$app/state';
  import SeasonInfo from '$lib/components/SeasonInfoSkeleton/SeasonInfoSkeleton.svelte';
  import ColorTable from '$lib/components/ColorTable/ColorTable.svelte';
  import SpoilerText from '$lib/components/SpoilerText/SpoilerText.svelte';
  import DownloadIcon from "@lucide/svelte/icons/download";
  import PauseIcon from "@lucide/svelte/icons/pause";
  import PlayIcon from "@lucide/svelte/icons/play";
  import Trash2Icon from "@lucide/svelte/icons/trash-2";

  const highlightId = $derived(page.url.searchParams.get("id") ?? undefined);

  const posters = import.meta.glob('$data/eps-metadata/One Pace/Season */poster.png', { eager: true, import: 'default' });

  function getPoster(seasonId: string | undefined) {
    const match = Object.entries(posters).find(([path]) => path.includes(`Season ${seasonId}/`));
    return match?.[1];
  }

  const pageData = {
    imagePath: getPoster(page.params.id),
    title: 'Romance Dawn',
    description: 'Monkey D. Luffy sets out on an adventure to form a crew, find the legendary One Piece, and become the pirate king.',
    episodes: [
      { ep_id: 1, season: page.params.id, number: 1, title: 'Romance Dawn, the Dawn of an Adventure', duration: '24 min', status: 'Hardlinked' },
      { ep_id: 2, season: page.params.id, number: 2, title: 'They Call Him Straw Hat Luffy', duration: '22 min', status: 'Copied' },
      { ep_id: 3, season: page.params.id, number: 3, title: 'The Pirate King and the Master Swordsman', duration: '23 min', status: 'Downloading' },
      { ep_id: 4, season: page.params.id, number: 4, title: 'The First', duration: '24 min', status: 'Error' },
      { ep_id: 5, season: page.params.id, number: 5, title: 'Extra', duration: '22 min', status: 'Not Downloaded' },
    ]
  }

  let isDownloadRunning = $state(false);
</script>

<div class="flex flex-col gap-6">
  <SeasonInfo seasonNum={page.params.id} title={pageData.title} imagePath={pageData.imagePath} description={pageData.description} />
  <ColorTable data={pageData.episodes} searchBox={true} searchableFields={['number', 'title']} highlightId={highlightId} idKey="ep_id">
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
