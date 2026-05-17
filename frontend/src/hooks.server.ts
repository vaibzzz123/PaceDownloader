import { error, redirect, type Handle } from '@sveltejs/kit';
import { PUBLIC_BACKEND_URL } from '$env/static/public';

import type { components } from '$lib/types/api';

type SetupStatusResponse = components['schemas']['SetupStatusResponse'];

export const handle: Handle = async ({ event, resolve }) => {
  let response: Response;

  try {
    response = await event.fetch(`${PUBLIC_BACKEND_URL}/setup/status`);
  } catch {
    error(503, 'Could not reach Pace Downloader backend');
  }

  if (!response.ok) {
    error(response.status, 'Failed to load setup status');
  }

  const setupStatus: SetupStatusResponse = await response.json();

  if (setupStatus.required && event.url.pathname !== '/setup') {
    redirect(307, '/setup');
  }

  return resolve(event);
};
