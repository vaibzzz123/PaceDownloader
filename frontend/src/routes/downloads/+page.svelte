<script lang="ts">
  import { page } from "$app/state";
  import { Tabs } from "@skeletonlabs/skeleton-svelte";
  import EpisodeDownloads from "$lib/components/EpisodeDownloads/EpisodeDownloads.svelte";
  import TorrentDownloads from "$lib/components/TorrentDownloads/TorrentDownloads.svelte";
  import ColorTable from "$lib/components/ColorTable/ColorTable.svelte";

  const tab = $derived(page.url.searchParams.get("tab") ?? "episodes");
  const highlightId = $derived(page.url.searchParams.get("id") ?? undefined);

  const downloadsTableData = [
    { ep_id: 1, name: 'Romance Dawn, the Dawn of an Adventure', extended: true, status: 'Downloading', progress: 50, torrent_id: 1, torrent_name: 'Romance Dawn' },
    { ep_id: 2, name: 'Episode 2', extended: false, status: 'Download Complete', progress: 100, torrent_id: 1, torrent_name: 'Romance Dawn' },
    { ep_id: 3, name: 'Episode 3', extended: false, status: 'Error', progress: 0, torrent_id: 3, torrent_name: 'Syrup Village' },
    { ep_id: 4, name: 'Episode 4', extended: false, status: 'Paused', progress: 25, torrent_id: 2, torrent_name: 'Orange Town' },
    { ep_id: 5, name: 'Episode 5', extended: false, status: 'Hardlinked', progress: 100, torrent_id: 1, torrent_name: 'Romance Dawn' },
    { ep_id: 6, name: 'Episode 6', extended: false, status: 'Copied', progress: 100, torrent_id: 2, torrent_name: 'Orange Town' },
  ];
</script>

<h1 class="-mt-2 text-2xl font-bold">Downloads</h1>
<Tabs value={tab}>
  <Tabs.List>
    <Tabs.Trigger class="flex-1" value="episodes">
      {#snippet element(attributes: Record<string, unknown>)}
        <a href="/downloads?tab=episodes" {...attributes}>Episodes</a>
      {/snippet}
    </Tabs.Trigger>
    <Tabs.Trigger class="flex-1" value="torrents">
      {#snippet element(attributes: Record<string, unknown>)}
        <a href="/downloads?tab=torrents" {...attributes}>Torrents</a>
      {/snippet}
    </Tabs.Trigger>
  </Tabs.List>
  <Tabs.Content value="episodes">
    <!-- <EpisodeDownloads {highlightId} /> -->
    <ColorTable data={downloadsTableData}
    spoilerName={true}
    headerMappings={{
      ep_id: 'Episode ID',
    }}
    actionsColumn={true}
    hiddenColumns={['torrent_id']}
    />
  </Tabs.Content>
  <Tabs.Content value="torrents">
    <TorrentDownloads {highlightId} />
  </Tabs.Content>
</Tabs>
