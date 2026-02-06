<script lang="ts">
  import { page } from '$app/state';
  import { Tabs } from '@skeletonlabs/skeleton-svelte';
  import EpisodeDownloads from '$lib/components/EpisodeDownloads/EpisodeDownloads.svelte';
  import TorrentDownloads from '$lib/components/TorrentDownloads/TorrentDownloads.svelte';

  const tab = $derived(page.url.searchParams.get('tab') ?? 'episodes');
  const highlightId = $derived(page.url.searchParams.get('id') ?? undefined);
</script>

<h1 class="-mt-2 text-2xl font-bold">Downloads</h1>
<Tabs value={tab}>
  <Tabs.List>
    <Tabs.Trigger value="episodes">
      {#snippet element(attributes: Record<string, unknown>)}
        <a href="/downloads?tab=episodes" {...attributes}>Episodes</a>
      {/snippet}
    </Tabs.Trigger>
    <Tabs.Trigger value="torrents">
      {#snippet element(attributes: Record<string, unknown>)}
        <a href="/downloads?tab=torrents" {...attributes}>Torrents</a>
      {/snippet}
    </Tabs.Trigger>
  </Tabs.List>
  <Tabs.Content value="episodes">
    <EpisodeDownloads {highlightId}/>
  </Tabs.Content>
  <Tabs.Content value="torrents">
    <TorrentDownloads {highlightId} />
  </Tabs.Content>
</Tabs>
