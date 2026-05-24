import { proxyBackendRequest } from '$lib/server/backend';
import type { RequestHandler } from './$types';

const POSTERS_PREFIX = '/posters';

const proxy: RequestHandler = async ({ request, url }) => {
  const backendPath = url.pathname.slice(POSTERS_PREFIX.length) || '/';
  return proxyBackendRequest(request, `/posters${backendPath}`, url.search);
};

export const GET = proxy;
export const HEAD = proxy;
