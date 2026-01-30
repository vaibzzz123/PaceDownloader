<script>
  import { page } from '$app/state';
  import EpisodeList from '$lib/components/EpisodeList/EpisodeList.svelte';

  const pageData = {
    imagePath: '../../../backend/data/eps-metadata/One Pace/Season 1/poster.png',
    title: 'Romance Dawn',
    episodes: [
      { number: 1, title: 'Romance Dawn, the Dawn of an Adventure', duration: '24 min', status: 'Hardlinked' },
      { number: 2, title: 'They Call Him Straw Hat Luffy', duration: '22 min', status: 'Copied' },
      { number: 3, title: 'The Pirate King and the Master Swordsman', duration: '23 min', status: 'Downloading' },
      { number: 4, title: 'The First', duration: '24 min', status: 'Not Downloaded' },
    ]
  }
</script>

<EpisodeList episodes={pageData.episodes} season={page.params.id} />