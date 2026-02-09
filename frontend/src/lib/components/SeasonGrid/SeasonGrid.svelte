<script lang="ts">
  import SeasonCard from "../SeasonCardSkeleton/SeasonCardSkeleton.svelte";

  let { seasons } = $props();

  // Load poster images client-side using Vite's import.meta.glob
  const posterModules: Record<string, string> = import.meta.glob(
    '$data/eps-metadata/One Pace/Season */poster.png',
    { eager: true, import: 'default' }
  );

  // Merge server data with client-side images
  const seasonsWithImages = $derived(seasons.map(season => ({
    ...season,
    imagePath: season.imagePath || Object.entries(posterModules).find(([path]) =>
      path.includes(`Season ${season.seasonNum}/`)
    )?.[1]
  })));
</script>

<div class="flex flex-wrap gap-6">
  {#each seasonsWithImages as season}
    <SeasonCard {...season} gridMode={true}/>
  {/each}
</div>