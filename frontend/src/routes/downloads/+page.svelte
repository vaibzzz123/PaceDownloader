<script lang="ts">
  import { page } from "$app/state";
  import { Tabs } from "@skeletonlabs/skeleton-svelte";
  import ColorTable from "$lib/components/ColorTable/ColorTable.svelte";
  import PauseIcon from "@lucide/svelte/icons/pause";
  import PlayIcon from "@lucide/svelte/icons/play";
  import Trash2Icon from "@lucide/svelte/icons/trash-2";
  import SpoilerText from "$lib/components/SpoilerText/SpoilerText.svelte";
  import DownloadProgress from "$lib/components/DownloadProgress/DownloadProgress.svelte";

  const highlightId = $derived(page.url.searchParams.get("id") ?? undefined);

  const episodeDownloadsTableData = [
    { ep_id: 1, season: 1, name: 'Romance Dawn, the Dawn of an Adventure', extended: true, status: 'Downloading', progress: 50, torrent_id: 1, torrent_name: 'Romance Dawn' },
    { ep_id: 2, season: 1, name: 'Episode 2', extended: false, status: 'Download Complete', progress: 100, torrent_id: 1, torrent_name: 'Romance Dawn' },
    { ep_id: 3, season: 3, name: 'Episode 3', extended: false, status: 'Error', progress: 0, torrent_id: 3, torrent_name: 'Syrup Village' },
    { ep_id: 4, season: 2, name: 'Episode 4', extended: false, status: 'Paused', progress: 25, torrent_id: 2, torrent_name: 'Orange Town' },
    { ep_id: 5, season: 1, name: 'Episode 5', extended: false, status: 'Hardlinked', progress: 100, torrent_id: 1, torrent_name: 'Romance Dawn' },
    { ep_id: 6, season: 2, name: 'Episode 6', extended: false, status: 'Copied', progress: 100, torrent_id: 2, torrent_name: 'Orange Town' },
  ];

  const torrentDownloadsTableData = [
    { id: 1, name: 'Romance Dawn', status: 'Downloading', progress: 50, ep_ids: [1, 2], ep_names: ['Romance Dawn, the Dawn of an Adventure', 'Episode 2'] },
    { id: 2, name: 'Orange Town', status: 'Paused', progress: 25, ep_ids: [4], ep_names: ['Episode 4'] },
    { id: 3, name: 'Syrup Village', status: 'Error', progress: 0, ep_ids: [3], ep_names: ['Episode 3'] },
  ];

  let isDownloadRunning = $state(false);

</script>

<h1 class="-mt-2 text-2xl font-bold">Downloads</h1>
{#key page.url.search}
<!-- Need to do this onValueChange to update the URL when the tab changes, at the browser level above SvelteKit -->
<Tabs defaultValue={page.url.searchParams.get("tab") ?? "episodes"} onValueChange={(details) => history.replaceState(null, '', `?tab=${details.value}`)}>
  <Tabs.List>
    <Tabs.Trigger class="flex-1" value="episodes">Episodes</Tabs.Trigger>
    <Tabs.Trigger class="flex-1" value="torrents">Torrents</Tabs.Trigger>
    <Tabs.Indicator />
  </Tabs.List>
  <Tabs.Content value="episodes">
    <span class="mb-3 chip bg-black/10 dark:bg-white/20 hover:bg-black/20 dark:hover:bg-white/20">Note: Pausing/resuming an episode download will pause/resume the entire torrent, potentially affecting other episodes in the same torrent.</span>
    <ColorTable data={episodeDownloadsTableData} searchBox={true} searchableFields={['ep_id', 'name','extended', 'status', 'torrent_id', 'torrent_name']} highlightId={highlightId} idKey="ep_id">
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
        <td><a class="text-blue-500 hover:underline" href={`/season/${item.season}?id=${item.ep_id}`}>{item.ep_id}</a></td>        <td><a class="text-blue-500 hover:underline" href={`/season/${item.season}?id=${item.ep_id}`}><SpoilerText>{item.name}</SpoilerText></a></td>
        <td>{item.extended ? 'Yes' : 'No'}</td>
        <td>{item.status}</td>
        <td>
          <DownloadProgress value={item.progress} status={item.status} />
        </td>
        <td><a class="text-blue-500 hover:underline" href={`/downloads?tab=torrents&id=${item.torrent_id}`}>{item.torrent_name}</a></td>
        <td>
          <button class="btn-icon" onclick={() => isDownloadRunning = !isDownloadRunning}>{#if isDownloadRunning}<PauseIcon/>{:else}<PlayIcon/>{/if}</button>
          <button class="btn-icon"><Trash2Icon /></button>
        </td>
      {/snippet}
    </ColorTable>
  </Tabs.Content>
  <Tabs.Content value="torrents">
    <ColorTable data={torrentDownloadsTableData} searchBox={true} searchableFields={['name', 'status','ep_ids', 'ep_names']} highlightId={highlightId} idKey="id">
      {#snippet header()}
        <th>Name</th>
        <th>Status</th>
        <th>Download Progress</th>
        <th>Episodes</th>
        <th>Actions</th>
      {/snippet}
      {#snippet row(item)}
        <td>{item.name}</td>
        <td>{item.status}</td>
        <td>
          <DownloadProgress value={item.progress} status={item.status} />
        </td>
        <td>
          {#each item.ep_ids as ep_id, index}
            {#if index !== 0}
              &nbsp; <!-- adds whitespace separator -->
            {/if}
            <a class="text-blue-500 hover:underline" href={`/downloads/?tab=episodes&id=${ep_id}`}>{ep_id}</a>
          {/each}
        </td>
        <td>
          <button class="btn-icon" onclick={() => isDownloadRunning = !isDownloadRunning}>{#if isDownloadRunning}<PauseIcon/>{:else}<PlayIcon/>{/if}</button>
          <button class="btn-icon"><Trash2Icon /></button>
        </td>
      {/snippet}
    </ColorTable>
  </Tabs.Content>
</Tabs>
{/key}
