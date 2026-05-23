<script lang="ts">
  import { PUBLIC_BACKEND_URL } from '$env/static/public';
  import CheckIcon from '@lucide/svelte/icons/check';
  import SetupWizard from '$lib/components/SetupWizard/SetupWizard.svelte';

  import type { PageProps } from './$types';
  import type { components } from '$lib/types/api';

  let { data }: PageProps = $props();

  type AppStateResponse = components['schemas']['AppStateResponse'];
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

  async function fetchAppState(): Promise<AppStateResponse> {
    const response = await fetch(`${PUBLIC_BACKEND_URL}/app-state`);
    const body = await parseResponseBody(response);

    if (!response.ok) {
      throw new Error(errorTextFromBody(body, 'Failed to load app state.'));
    }

    return body as AppStateResponse;
  }

  async function saveSettings(payload: SettingsSaveRequest): Promise<AppStateResponse> {
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

    return fetchAppState();
  }
</script>

<main class="flex min-h-screen items-center justify-center px-4 py-8 sm:px-6 lg:px-8">
  {#if !data.appState.initial_setup_complete && data.appState.restart_required}
    <section class="card bg-surface-100-900 mx-auto flex w-full max-w-180 flex-col items-center gap-4 p-6 text-center shadow-xl sm:p-8">
      <div class="preset-filled-primary-500 flex size-12 items-center justify-center rounded-full">
        <CheckIcon class="size-6" />
      </div>
      <div class="flex flex-col gap-2">
        <p class="text-sm font-medium">Initial setup</p>
        <h1 class="text-2xl font-bold">Restart required</h1>
        <p class="text-sm">
          Restart the Pace Downloader backend or Docker container to apply the saved setup.
        </p>
      </div>
    </section>
  {:else}
    <SetupWizard
      settings={data.settings}
      appState={data.appState}
      {validateMedia}
      {validateQbittorrent}
      {validatePathMapping}
      {saveSettings}
    />
  {/if}
</main>
