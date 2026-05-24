import { error, redirect, type Handle } from '@sveltejs/kit';

import { getBackendUrl } from '$lib/server/backend';
import type { components } from '$lib/types/api';

type AppStateResponse = components['schemas']['AppStateResponse'];

// Don't need to do redirect stuff as these are API routes
const UNGUARDED_PATH_PREFIXES = ['/api', '/posters'];
const UNGUARDED_PATHS = new Set(['/health']);

export const handle: Handle = async ({ event, resolve }) => {
  if (isUnguardedPath(event.url.pathname)) {
    return resolve(event);
  }

  let response: Response;

  try {
    response = await event.fetch(getBackendUrl('/app-state'));
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

function isUnguardedPath(pathname: string): boolean {
  return (
    UNGUARDED_PATHS.has(pathname) ||
    UNGUARDED_PATH_PREFIXES.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`))
  );
}
