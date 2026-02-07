<script lang="ts">
  import { page } from "$app/state";
  import { Tabs } from "@skeletonlabs/skeleton-svelte";
  import TorrentDownloads from "$lib/components/TorrentDownloads/TorrentDownloads.svelte";
  import ColorTable from "$lib/components/ColorTable/ColorTable.svelte";
  import DownloadIcon from "@lucide/svelte/icons/download";
  import PauseIcon from "@lucide/svelte/icons/pause";
  import PlayIcon from "@lucide/svelte/icons/play";
  import Trash2Icon from "@lucide/svelte/icons/trash-2";

  const highlightId = $derived(page.url.searchParams.get("id") ?? undefined);

  const downloadsTableData = [
    { ep_id: 1, name: 'Romance Dawn, the Dawn of an Adventure', extended: true, status: 'Downloading', progress: 50, torrent_id: 1, torrent_name: 'Romance Dawn' },
    { ep_id: 2, name: 'Episode 2', extended: false, status: 'Download Complete', progress: 100, torrent_id: 1, torrent_name: 'Romance Dawn' },
    { ep_id: 3, name: 'Episode 3', extended: false, status: 'Error', progress: 0, torrent_id: 3, torrent_name: 'Syrup Village' },
    { ep_id: 4, name: 'Episode 4', extended: false, status: 'Paused', progress: 25, torrent_id: 2, torrent_name: 'Orange Town' },
    { ep_id: 5, name: 'Episode 5', extended: false, status: 'Hardlinked', progress: 100, torrent_id: 1, torrent_name: 'Romance Dawn' },
    { ep_id: 6, name: 'Episode 6', extended: false, status: 'Copied', progress: 100, torrent_id: 2, torrent_name: 'Orange Town' },
  ];

  let isDownloadRunning = $state(false);
</script>

<h1 class="-mt-2 text-2xl font-bold">Downloads</h1>
{#key page.url.search}
<Tabs defaultValue={page.url.searchParams.get("tab") ?? "episodes"}>
  <Tabs.List>
    <Tabs.Trigger class="flex-1" value="episodes">Episodes</Tabs.Trigger>
    <Tabs.Trigger class="flex-1" value="torrents">Torrents</Tabs.Trigger>
    <Tabs.Indicator />
  </Tabs.List>
  <Tabs.Content value="episodes">
    <ColorTable data={downloadsTableData}>
      {#snippet header()}
        <th>Episode ID</th>
        <th>Name</th>
        <th>Extended</th>
        <th>Status</th>
        <th>Progress</th>
        <th>Torrent</th>
        <th>Actions</th>
      {/snippet}
      {#snippet row(item)}
        <td>{item.ep_id}</td>
        <td>{item.name}</td>
        <td>{item.extended ? 'Yes' : 'No'}</td>
        <td>{item.status}</td>
        <td>{item.progress}%</td>
        <td><a href={`/downloads?tab=torrents&id=${item.torrent_id}`}>{item.torrent_name}</a></td>
        <td>
          <button class="btn-icon" disabled={isDownloadRunning}><DownloadIcon /></button>
          <button class="btn-icon" onclick={() => isDownloadRunning = !isDownloadRunning}>{#if isDownloadRunning}<PauseIcon/>{:else}<PlayIcon/>{/if}</button>
          <button class="btn-icon"><Trash2Icon /></button>
        </td>
      {/snippet}
    </ColorTable>
  </Tabs.Content>
  <Tabs.Content value="torrents">
    <TorrentDownloads {highlightId} />
  </Tabs.Content>
</Tabs>
{/key}
