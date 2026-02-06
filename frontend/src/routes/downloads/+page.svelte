<script lang="ts">
  import { Tabs } from '@skeletonlabs/skeleton-svelte';
  import EpisodeDownloads from '$lib/components/EpisodeDownloads/EpisodeDownloads.svelte';
  import TorrentDownloads from '$lib/components/TorrentDownloads/TorrentDownloads.svelte';
</script>

<h1 class="text-2xl font-bold">Downloads</h1>
<Tabs defaultValue="Episodes">
  <Tabs.List>
    <Tabs.Trigger value="Episodes">Episodes</Tabs.Trigger>
    <Tabs.Trigger value="Torrents">Torrents</Tabs.Trigger>
  </Tabs.List>
  <Tabs.Content value="Episodes">
    <EpisodeDownloads />
  </Tabs.Content>
  <Tabs.Content value="Torrents">
    <TorrentDownloads />
  </Tabs.Content>
</Tabs>