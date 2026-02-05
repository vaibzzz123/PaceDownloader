<script lang="ts">
  // import SeasonCard from "../SeasonCard/SeasonCard.svelte";
  import SeasonCard from "../SeasonCardSkeleton/SeasonCardSkeleton.svelte";

  // Glob import posters and season NFOs
  const posterModules: Record<string, string> = import.meta.glob(
    '$data/eps-metadata/One Pace/Season */poster.png',
    { eager: true, import: 'default' }
  );

  const nfoModules: Record<string, string> = import.meta.glob(
    '$data/eps-metadata/One Pace/Season */season.nfo',
    { eager: true, as: 'raw' }
  );

  // Parse season title from NFO XML (e.g. "1. Romance Dawn" -> "Romance Dawn")
  function parseTitle(nfoContent: string): string {
    const match = nfoContent.match(/<title>(?:\d+\.\s*)?(.+?)<\/title>/);
    return match ? match[1] : 'Unknown';
  }

  // Extract season number from path (e.g. ".../Season 12/..." -> 12)
  function getSeasonNum(path: string): number {
    const match = path.match(/Season (\d+)\//);
    return match ? parseInt(match[1]) : 0;
  }

  // Build season list from NFO files, sorted by season number
  const seasonInfo = Object.entries(nfoModules)
    .map(([path, content]) => ({
      seasonNum: getSeasonNum(path),
      title: parseTitle(content),
      imagePath: Object.entries(posterModules).find(([p]) =>
        p.includes(`Season ${getSeasonNum(path)}/`)
      )?.[1],
    }))
    .sort((a, b) => a.seasonNum - b.seasonNum);
</script>

<div class="flex flex-wrap gap-6 m-10">
  {#each seasonInfo as season}
    <SeasonCard {...season} />
  {/each}
</div>