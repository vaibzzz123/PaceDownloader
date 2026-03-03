import { error } from '@sveltejs/kit';
import { PUBLIC_BACKEND_URL } from '$env/static/public';

import type { PageServerLoad } from './$types';
import type { components } from '$lib/types/api';

type SeasonResponse = components['schemas']['SeasonResponse'];
type EpisodeResponse = components['schemas']['EpisodeResponse'];

export const load: PageServerLoad = async ({ fetch, params }) => {
  const [seasonRes, episodesRes] = await Promise.all([
    fetch(`${PUBLIC_BACKEND_URL}/season/${params.id}`),
    fetch(`${PUBLIC_BACKEND_URL}/season/${params.id}/episodes`),
  ]);

  if (!seasonRes.ok) error(seasonRes.status, 'Failed to load season');
  if (!episodesRes.ok) error(episodesRes.status, 'Failed to load episodes');

  const season: SeasonResponse = await seasonRes.json();
  const episodes: EpisodeResponse[] = await episodesRes.json();

  season.image = `${PUBLIC_BACKEND_URL}${season.image}`;
  return { season, episodes };
};
