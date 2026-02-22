import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import type { components } from '$lib/types/api';
type SeasonResponse = components['schemas']['SeasonResponse'];

const API_URL = 'http://localhost:8000';

export const load: PageServerLoad = async ({ fetch, params }) => {
  const response = await fetch(`${API_URL}/season/${params.id}`);
  if (!response.ok) error(response.status, 'Failed to load season');
  const season: SeasonResponse = await response.json();

  season.image = `${API_URL}${season.image}`;
  return { season };
};
