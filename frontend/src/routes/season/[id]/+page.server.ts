import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import type { components } from '$lib/types/api';
type SeasonResponse = components['schemas']['SeasonResponse'];
type EpisodeResponse = components['schemas']['EpisodeResponse'];

const API_URL = 'http://localhost:8000';

export const load: PageServerLoad = async ({ fetch, params }) => {
  const [seasonRes, episodesRes] = await Promise.all([
    fetch(`${API_URL}/season/${params.id}`),
    fetch(`${API_URL}/season/${params.id}/episodes`),
  ]);

  if (!seasonRes.ok) error(seasonRes.status, 'Failed to load season');
  if (!episodesRes.ok) error(episodesRes.status, 'Failed to load episodes');

  const season: SeasonResponse = await seasonRes.json();
  const episodes: EpisodeResponse[] = await episodesRes.json();

  season.image = `${API_URL}${season.image}`;
  return { season, episodes };
};
