import { error } from '@sveltejs/kit';
import { PUBLIC_BACKEND_URL } from '$env/static/public';

import type { PageServerLoad } from './$types';
import type { components } from '$lib/types/api';

type SeasonResponse = components['schemas']['SeasonResponse'];

export const load: PageServerLoad = async ({ fetch }) => {
  const response = await fetch(`${PUBLIC_BACKEND_URL}/season`);
  if (!response.ok) error(response.status, 'Failed to load seasons');
  const seasons : SeasonResponse[] = await response.json();

  // append api url to each season image
  seasons.forEach(season => {
    season.image = `${PUBLIC_BACKEND_URL}${season.image}`;
  });
  return { seasons };
};