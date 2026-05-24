import { error } from '@sveltejs/kit';
import { getBackendUrl } from '$lib/server/backend';

import type { PageServerLoad } from './$types';
import type { components } from '$lib/types/api';

type SeasonResponse = components['schemas']['SeasonResponse'];

export const load: PageServerLoad = async ({ fetch }) => {
  const response = await fetch(getBackendUrl('/season'));
  if (!response.ok) error(response.status, 'Failed to load seasons');
  const seasons : SeasonResponse[] = await response.json();
  return { seasons };
};
