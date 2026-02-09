import type { PageServerLoad } from './$types';
import { readdir, readFile } from 'fs/promises';
import { join } from 'path';


// Parse season title from NFO XML (e.g. "1. Romance Dawn" -> "Romance Dawn")
function parseTitle(nfoContent: string): string {
  const match = nfoContent.match(/<title>(?:\d+\.\s*)?(.+?)<\/title>/);
  return match ? match[1] : 'Unknown';
}

// Extract season number from directory name (e.g. "Season 12" -> 12)
function getSeasonNum(dirName: string): number {
  const match = dirName.match(/Season (\d+)/);
  return match ? parseInt(match[1]) : 0;
}

const getSeasons = async () => {
  const basePath = join(process.cwd(), '..', 'backend', 'data', 'eps-metadata', 'One Pace');

  try {
    // Read all entries in the One Pace directory
    const entries = await readdir(basePath, { withFileTypes: true });

    // Filter for Season directories
    const seasonDirs = entries.filter(
      entry => entry.isDirectory() && entry.name.startsWith('Season ')
    );

    // Load data for each season
    const seasons = await Promise.all(
      seasonDirs.map(async (dir) => {
        const seasonNum = getSeasonNum(dir.name);
        const seasonPath = join(basePath, dir.name);

        // Read NFO file
        let title = 'Unknown';
        try {
          const nfoContent = await readFile(join(seasonPath, 'season.nfo'), 'utf-8');
          title = parseTitle(nfoContent);
        } catch (error) {
          console.error(`Failed to read NFO for ${dir.name}:`, error);
        }

        return {
          seasonNum,
          title,
          imagePath: undefined // Images loaded client-side via Vite
        };
      })
    );

    return seasons.sort((a, b) => a.seasonNum - b.seasonNum);
  } catch (error) {
    console.error('Failed to load season data:', error);
    return [];
  }
};

export const load: PageServerLoad = async () => {
  return {
    seasons: await getSeasons()
  };
};