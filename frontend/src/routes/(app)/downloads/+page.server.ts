import { error } from '@sveltejs/kit';
import { getBackendUrl } from '$lib/server/backend';

import type { PageServerLoad } from './$types';
import type { components } from '$lib/types/api';

type EpisodeDownloadResponse = components['schemas']['EpisodeDownloadResponse'];
type TorrentDownloadResponse = components['schemas']['TorrentDownloadResponse'];

export const load: PageServerLoad = async ({ fetch }) => {
  const [episodesRes, torrentsRes] = await Promise.all([
    fetch(getBackendUrl('/episode')),
    fetch(getBackendUrl('/torrent')),
  ]);

  if (!episodesRes.ok) error(episodesRes.status, 'Failed to load episode downloads');
  if (!torrentsRes.ok) error(torrentsRes.status, 'Failed to load torrent downloads');

  const episodes: EpisodeDownloadResponse[] = await episodesRes.json();
  const torrents: TorrentDownloadResponse[] = await torrentsRes.json();

  return { episodes, torrents };
};
