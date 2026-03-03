import { error } from '@sveltejs/kit';
import { PUBLIC_BACKEND_URL } from '$env/static/public';

import type { PageServerLoad } from './$types';
import type { components } from '$lib/types/api';

type EpisodeDownloadResponse = components['schemas']['EpisodeDownloadResponse'];
type TorrentDownloadResponse = components['schemas']['TorrentDownloadResponse'];

export const load: PageServerLoad = async ({ fetch }) => {
  const [episodesRes, torrentsRes] = await Promise.all([
    fetch(`${PUBLIC_BACKEND_URL}/episode`),
    fetch(`${PUBLIC_BACKEND_URL}/torrent`),
  ]);

  if (!episodesRes.ok) error(episodesRes.status, 'Failed to load episode downloads');
  if (!torrentsRes.ok) error(torrentsRes.status, 'Failed to load torrent downloads');

  const episodes: EpisodeDownloadResponse[] = await episodesRes.json();
  const torrents: TorrentDownloadResponse[] = await torrentsRes.json();

  return { episodes, torrents };
};
