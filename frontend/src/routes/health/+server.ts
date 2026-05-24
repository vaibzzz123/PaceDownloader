import { json } from '@sveltejs/kit';
import { getBackendUrl } from '$lib/server/backend';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ fetch }) => {
  try {
    const response = await fetch(getBackendUrl('/health'));

    return json({
      status: 'ok',
      backend: {
        reachable: true,
        status: response.status,
      },
    });
  } catch {
    return json(
      {
        status: 'unavailable',
        backend: {
          reachable: false,
        },
      },
      { status: 503 }
    );
  }
};
