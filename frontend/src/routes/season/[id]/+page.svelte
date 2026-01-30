<script>
  import { page } from '$app/state';
  import EpisodeList from '$lib/components/EpisodeList/EpisodeList.svelte';

  const pageData = {
    imagePath: '../../../backend/data/eps-metadata/One Pace/Season 1/poster.png',
    title: 'Romance Dawn',
    episodes: [
      { number: 1, title: 'Romance Dawn, the Dawn of an Adventure', duration: '24 min', downloaded: true },
      { number: 2, title: 'They Call Him Straw Hat Luffy', duration: '22 min', downloaded: false },
    ]
  }
</script>

<EpisodeList episodes={pageData.episodes} season={page.params.id} />