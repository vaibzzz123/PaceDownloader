<script lang="ts">
  import { page } from '$app/state';
  import SeasonInfo from '$lib/components/SeasonInfoSkeleton/SeasonInfoSkeleton.svelte';
  import ColorTable from '$lib/components/ColorTable/ColorTable.svelte';

  const posters = import.meta.glob('$data/eps-metadata/One Pace/Season */poster.png', { eager: true, import: 'default' });

  function getPoster(seasonId: string | undefined) {
    const match = Object.entries(posters).find(([path]) => path.includes(`Season ${seasonId}/`));
    return match?.[1];
  }

  const pageData = {
    imagePath: getPoster(page.params.id),
    title: 'Romance Dawn',
    description: 'Monkey D. Luffy sets out on an adventure to form a crew, find the legendary One Piece, and become the pirate king.',
    // description: `Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna
    // aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure
    // dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident,
    // sunt in culpa qui officia deserunt mollit anim id est laborum.`,
    // description: "The Straw Hats' next destination is Fishman Island, but first they must traverse the dreaded Florian Triangle which is known for many eerie and mysterious things such as disappearing crews, conversational skeletons, and a floating island full of zombies and other horrors.",
    episodes: [
      { ep_id: 1, season: page.params.id, number: 1, title: 'Romance Dawn, the Dawn of an Adventure', duration: '24 min', status: 'Hardlinked' },
      { ep_id: 2, season: page.params.id, number: 2, title: 'They Call Him Straw Hat Luffy', duration: '22 min', status: 'Copied' },
      { ep_id: 3, season: page.params.id, number: 3, title: 'The Pirate King and the Master Swordsman', duration: '23 min', status: 'Downloading' },
      { ep_id: 4, season: page.params.id, number: 4, title: 'The First', duration: '24 min', status: 'Error' },
      { ep_id: 5, season: page.params.id, number: 5, title: 'Extra', duration: '22 min', status: 'Not Downloaded' },
    ]
  }
</script>

<div class="flex flex-col gap-20">
  <SeasonInfo seasonNum={page.params.id} title={pageData.title} imagePath={pageData.imagePath} description={pageData.description} />
  <ColorTable 
    data={pageData.episodes}
    spoilerName={true}
    headerMappings={{
      title: 'Name',
    }}
    actionsColumn={true}
    hiddenColumns={['ep_id']}
  />
</div>