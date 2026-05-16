<script lang="ts">
  import { PUBLIC_BACKEND_URL } from '$env/static/public';
  import SetupWizard from "$lib/components/SetupWizard/SetupWizard.svelte";

  import type { PageProps } from './$types';
  import type { components } from '$lib/types/api';

  let { data }: PageProps = $props();

  type SettingsSaveRequest = components['schemas']['SettingsSaveRequest'];
  type SetupMediaValidationRequest = components['schemas']['SetupMediaValidationRequest'];
  type SetupQbittorrentValidationRequest =
    components['schemas']['SetupQbittorrentValidationRequest'];
  type SetupPathMappingValidationRequest =
    components['schemas']['SetupPathMappingValidationRequest'];
  type SetupValidationResponse = components['schemas']['SetupValidationResponse'];

  // TODO: See how to simplify this text extraction from backend by making a simpler data structure
  function errorTextFromBody(body: unknown, fallback: string): string {
    if (body && typeof body === 'object' && 'detail' in body) {
      const { detail } = body as { detail: unknown };

      if (typeof detail === 'string') return detail;
      if (Array.isArray(detail)) {
        return detail
          .map((item) => {
            if (item && typeof item === 'object' && 'msg' in item) {
              return String((item as { msg: unknown }).msg);
            }
            return String(item);
          })
          .join(' ');
      }
    }

    if (body && typeof body === 'object' && 'message' in body) {
      return String((body as { message: unknown }).message);
    }

    return fallback;
  }

  async function parseResponseBody(response: Response): Promise<unknown> {
    try {
      return await response.json();
    } catch {
      return null;
    }
  }

  async function postValidation(
    path: string,
    payload:
      | SetupMediaValidationRequest
      | SetupQbittorrentValidationRequest
      | SetupPathMappingValidationRequest
  ): Promise<SetupValidationResponse> {
    let response: Response;

    try {
      response = await fetch(`${PUBLIC_BACKEND_URL}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    } catch {
      throw new Error('Could not reach the server. Check that Pace Downloader backend is running.');
    }

    const body = await parseResponseBody(response);

    if (!response.ok) {
      throw new Error(errorTextFromBody(body, 'Validation failed. Please check this step.'));
    }

    return body as SetupValidationResponse;
  }

  async function validateMedia(
    payload: SetupMediaValidationRequest
  ): Promise<SetupValidationResponse> {
    return postValidation('/setup/validate/media', payload);
  }

  async function validateQbittorrent(
    payload: SetupQbittorrentValidationRequest
  ): Promise<SetupValidationResponse> {
    return postValidation('/setup/validate/qbittorrent', payload);
  }

  async function validatePathMapping(
    payload: SetupPathMappingValidationRequest
  ): Promise<SetupValidationResponse> {
    return postValidation('/setup/validate/path-mapping', payload);
  }

  async function saveSettings(payload: SettingsSaveRequest): Promise<void> {
    let response: Response;

    try {
      response = await fetch(`${PUBLIC_BACKEND_URL}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    } catch {
      throw new Error('Could not reach the server. Check that Pace Downloader backend is running.');
    }

    const body = await parseResponseBody(response);

    if (!response.ok) {
      throw new Error(errorTextFromBody(body, 'Failed to save settings.'));
    }
  }
</script>

<main class="flex min-h-screen items-center justify-center px-4 py-8 sm:px-6 lg:px-8">
  <SetupWizard
    settings={data.settings}
    {validateMedia}
    {validateQbittorrent}
    {validatePathMapping}
    {saveSettings}
  />
</main>
