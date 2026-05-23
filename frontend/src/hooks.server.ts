import { error, redirect, type Handle } from '@sveltejs/kit';
import { PUBLIC_BACKEND_URL } from '$env/static/public';

import type { components } from '$lib/types/api';

type AppStateResponse = components['schemas']['AppStateResponse'];

export const handle: Handle = async ({ event, resolve }) => {
  let response: Response;

  try {
    response = await event.fetch(`${PUBLIC_BACKEND_URL}/app-state`);
  } catch {
    error(503, 'Could not reach Pace Downloader backend');
  }

  if (!response.ok) {
    error(response.status, 'Failed to load app state');
  }

  const appState: AppStateResponse = await response.json();

  if (!appState.initial_setup_complete && event.url.pathname !== '/setup') {
    redirect(307, '/setup');
  }

  return resolve(event);
};
