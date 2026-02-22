import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import type { components } from '$lib/types/api';
type SeasonResponse = components['schemas']['SeasonResponse'];

const API_URL = 'http://localhost:8000';

export const load: PageServerLoad = async ({ fetch }) => {
  const response = await fetch(`${API_URL}/season`);
  if (!response.ok) error(response.status, 'Failed to load seasons');
  const seasons : SeasonResponse[] = await response.json();

  // append api url to each season image
  seasons.forEach(season => {
    season.image = `${API_URL}${season.image}`;
  });
  return { seasons };
};