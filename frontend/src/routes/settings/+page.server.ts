import { error } from '@sveltejs/kit';
import { PUBLIC_BACKEND_URL } from '$env/static/public';
import type { PageServerLoad } from './$types';
import type { components } from '$lib/types/api';

type SettingsResponse = components['schemas']['SettingsResponse'];

export const load: PageServerLoad = async ({ fetch }) => {
  const res = await fetch(`${PUBLIC_BACKEND_URL}/settings`);
  if (!res.ok) error(res.status, 'Failed to load settings');
  const settings: SettingsResponse = await res.json();
  return { settings };
};
