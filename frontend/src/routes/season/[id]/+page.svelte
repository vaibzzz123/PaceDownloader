<script lang="ts">
  import { page } from '$app/state';
  import EpisodeList from '$lib/components/EpisodeListSkeleton/EpisodeListSkeleton.svelte';
  import SeasonInfo from '$lib/components/SeasonInfoSkeleton/SeasonInfoSkeleton.svelte';

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
      { number: 1, title: 'Romance Dawn, the Dawn of an Adventure', duration: '24 min', status: 'Hardlinked' },
      { number: 2, title: 'They Call Him Straw Hat Luffy', duration: '22 min', status: 'Copied' },
      { number: 3, title: 'The Pirate King and the Master Swordsman', duration: '23 min', status: 'Downloading' },
      { number: 4, title: 'The First', duration: '24 min', status: 'Not Downloaded' },
    ]
  }
</script>

<div class="flex flex-col gap-8">
  <SeasonInfo seasonNum={page.params.id} title={pageData.title} imagePath={pageData.imagePath} description={pageData.description} />
  <EpisodeList episodes={pageData.episodes} season={page.params.id} />
</div>