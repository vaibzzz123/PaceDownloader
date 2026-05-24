import { proxyBackendRequest } from '$lib/server/backend';
import type { RequestHandler } from './$types';

const API_PREFIX = '/api';

const proxy: RequestHandler = async ({ request, url }) => {
  const backendPath = url.pathname.slice(API_PREFIX.length) || '/';
  return proxyBackendRequest(request, backendPath, url.search);
};

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
export const HEAD = proxy;
