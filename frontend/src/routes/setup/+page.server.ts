import { error, redirect } from '@sveltejs/kit';
import { getBackendUrl } from '$lib/server/backend';

import type { PageServerLoad } from './$types';
import type { components } from '$lib/types/api';

type AppStateResponse = components['schemas']['AppStateResponse'];
type SettingsResponse = components['schemas']['SettingsResponse'];

export const load: PageServerLoad = async ({ fetch }) => {
  const [settingsRes, appStateRes] = await Promise.all([
    fetch(getBackendUrl('/settings')),
    fetch(getBackendUrl('/app-state')),
  ]);

  if (!settingsRes.ok) error(settingsRes.status, 'Failed to load settings');
  if (!appStateRes.ok) error(appStateRes.status, 'Failed to load app state');

  const settings: SettingsResponse = await settingsRes.json();
  const appState: AppStateResponse = await appStateRes.json();

  if (appState.initial_setup_complete) {
    redirect(307, '/');
  }

  return { settings, appState };
};
