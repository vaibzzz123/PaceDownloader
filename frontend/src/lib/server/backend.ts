import { env } from '$env/dynamic/private';

const DEFAULT_BACKEND_INTERNAL_URL = 'http://localhost:8000';
const BODYLESS_METHODS = new Set(['GET', 'HEAD']);
const HOP_BY_HOP_HEADERS = [
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
];

// duplex is so data can flow both ways
// half is so the request body can be streamed to backend
// apparently TS's RequestInit may not have duplex, so we need to extend it
type RequestInitWithDuplex = RequestInit & { duplex?: 'half' };

export function getBackendInternalUrl(): string {
  const configuredUrl = env.BACKEND_INTERNAL_URL?.trim();
  return (configuredUrl || DEFAULT_BACKEND_INTERNAL_URL).replace(/\/+$/, '');
}

export function getBackendUrl(pathname: string, search = ''): string {
  const normalizedPath = pathname.startsWith('/') ? pathname : `/${pathname}`;
  const url = new URL(normalizedPath, `${getBackendInternalUrl()}/`);
  url.search = search;
  return url.toString();
}

export async function proxyBackendRequest(
  request: Request,
  pathname: string,
  search = ''
): Promise<Response> {
  const headers = getProxyRequestHeaders(request.headers);
  const init: RequestInitWithDuplex = {
    method: request.method,
    headers,
    redirect: 'manual',
  };

  if (!BODYLESS_METHODS.has(request.method.toUpperCase())) {
    init.body = request.body;
    init.duplex = 'half';
  }

  try {
    const response = await fetch(getBackendUrl(pathname, search), init);
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: getProxyResponseHeaders(response.headers),
    });
  } catch {
    return new Response('Pace Downloader backend is unavailable', { status: 502 });
  }
}


// Removing some of these headers as they shouldn't be straight up forwarded
// Like host which will change, content-length which may differ
// Node's fetch recreates them in the proper manner for that request
function getProxyRequestHeaders(source: Headers): Headers {
  const headers = new Headers(source);
  headers.delete('host');
  headers.delete('content-length');

  for (const header of HOP_BY_HOP_HEADERS) {
    headers.delete(header);
  }

  return headers;
}

function getProxyResponseHeaders(source: Headers): Headers {
  const headers = new Headers(source);

  for (const header of HOP_BY_HOP_HEADERS) {
    headers.delete(header);
  }

  return headers;
}
