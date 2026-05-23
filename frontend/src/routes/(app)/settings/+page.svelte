<script lang="ts">
  import { PUBLIC_BACKEND_URL } from '$env/static/public';
  import AlertTriangleIcon from '@lucide/svelte/icons/alert-triangle';
  import type { PageProps } from './$types';

  let { data }: PageProps = $props();

  let appState = $derived(data.appState);
  let mediaDataLocation = $derived((data.settings.media_data_location.value as string) ?? '');
  let preferExtended = $derived(Boolean(data.settings.prefer_extended.value));
  let qbtHostname = $derived((data.settings.qbt_hostname.value as string) ?? '');
  let qbtUsername = $derived((data.settings.qbt_username.value as string) ?? '');
  let qbtPassword = $derived((data.settings.qbt_password.value as string) ?? '');
  let qbtPathLocal = $derived((data.settings.qbt_path_local.value as string) ?? '');
  let qbtPathRemote = $derived((data.settings.qbt_path_remote.value as string) ?? '');
  let qbtCategory = $derived((data.settings.qbt_category.value as string) ?? '');
  let qbtDownloadLocation = $derived((data.settings.qbt_download_location.value as string) ?? '');
  let qbtPollingRate = $derived((data.settings.qbt_polling_rate.value as number) ?? 8);
  let logLevel = $derived((data.settings.log_level.value as string) ?? 'INFO');

  let saveError = $state<string | null>(null);
  let saving = $state(false);
  let saved = $state(false);
  let restartRequired = $derived(
    appState.initial_setup_complete === true && appState.restart_required === true
  );

  async function fetchAppState() {
    const res = await fetch(`${PUBLIC_BACKEND_URL}/app-state`);
    if (!res.ok) throw new Error('Failed to load app state');
    appState = await res.json();
  }

  async function saveSettings() {
    saving = true;
    saveError = null;
    saved = false;
    try {
      const res = await fetch(`${PUBLIC_BACKEND_URL}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          media_data_location: mediaDataLocation,
          prefer_extended: preferExtended,
          qbt_hostname: qbtHostname,
          qbt_username: qbtUsername,
          qbt_password: qbtPassword,
          qbt_path_local: qbtPathLocal || null,
          qbt_path_remote: qbtPathRemote || null,
          qbt_category: qbtCategory || null,
          qbt_download_location: qbtDownloadLocation || null,
          qbt_polling_rate: qbtPollingRate,
          log_level: logLevel,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        saveError = body.detail ?? 'Failed to save settings';
      } else {
        await fetchAppState();
        saved = !restartRequired;
      }
    } catch {
      saveError = 'Could not reach the server';
    } finally {
      saving = false;
    }
  }
</script>

{#snippet envChip()}
<span class="preset-tonal-warning mt-2 w-fit text-xs inline-flex items-center gap-2 rounded py-1 px-3 transition-all hover:brightness-90">
  <AlertTriangleIcon size={15}/><p>Set via environment variable — remove it to edit this setting.</p>
</span>
{/snippet}

<h1 class="-mt-2 text-2xl font-bold">Settings</h1>

{#if saveError}
  <div class="preset-tonal-error rounded p-3 text-sm mt-3">{saveError}</div>
{/if}
{#if restartRequired}
  <div class="preset-tonal-warning rounded p-3 text-sm mt-3 flex max-w-3xl items-start gap-2">
    <AlertTriangleIcon class="size-5 shrink-0" />
    <span>Restart the Pace Downloader backend or Docker container to apply these settings.</span>
  </div>
{/if}
{#if saved}
  <div class="preset-tonal-success rounded p-3 text-sm mt-3">Settings saved.</div>
{/if}

<form class="flex flex-col gap-6 mt-4">

  <section class="flex flex-col gap-3">
    <h2 class="text-lg font-semibold">General</h2>
    <label class="label">
      <span class="label-text flex items-center gap-2">
        Media Data Location
      </span>
      <input
        class="input border border-surface-600 bg-surface-50-950 text-surface-950-50 placeholder:text-black/40 dark:placeholder:text-white/40 disabled:cursor-not-allowed disabled:bg-surface-100-900 disabled:text-surface-950-50 disabled:opacity-100 w-80"
        type="text"
        bind:value={mediaDataLocation}
        disabled={data.settings.media_data_location.env_override}
      />
      {#if data.settings.media_data_location.env_override}{@render envChip()}{/if}
    </label>
    <label class="label w-fit">
      <span class="label-text flex items-center gap-2">
        Prefer Extended
      </span>
      <input
        class="checkbox disabled:cursor-not-allowed disabled:opacity-60"
        type="checkbox"
        bind:checked={preferExtended}
        disabled={data.settings.prefer_extended.env_override}
      />
      {#if data.settings.prefer_extended.env_override}{@render envChip()}{/if}
    </label>
    <label class="label w-fit">
      <span class="label-text flex items-center gap-2">
        Log Level
      </span>
      <select class="select border border-surface-600 bg-surface-50-950 text-surface-950-50 placeholder:text-black/40 dark:placeholder:text-white/40 disabled:cursor-not-allowed disabled:bg-surface-100-900 disabled:text-surface-950-50 disabled:opacity-100 pl-3" bind:value={logLevel} disabled={data.settings.log_level.env_override}>
        <option value="DEBUG">DEBUG</option>
        <option value="INFO">INFO</option>
        <option value="WARNING">WARNING</option>
        <option value="ERROR">ERROR</option>
      </select>
      {#if data.settings.log_level.env_override}{@render envChip()}{/if}
    </label>
  </section>

  <section class="flex flex-col gap-3">
    <h2 class="text-lg font-semibold">qBittorrent</h2>
    <label class="label">
      <span class="label-text flex items-center gap-2">
        Hostname
      </span>
      <input
        class="input border border-surface-600 bg-surface-50-950 text-surface-950-50 placeholder:text-black/40 dark:placeholder:text-white/40 disabled:cursor-not-allowed disabled:bg-surface-100-900 disabled:text-surface-950-50 disabled:opacity-100 w-80"
        type="text"
        bind:value={qbtHostname}
        disabled={data.settings.qbt_hostname.env_override}
      />
      {#if data.settings.qbt_hostname.env_override}{@render envChip()}{/if}
    </label>
    <label class="label">
      <span class="label-text flex items-center gap-2">
        Username
      </span>
      <input
        class="input border border-surface-600 bg-surface-50-950 text-surface-950-50 placeholder:text-black/40 dark:placeholder:text-white/40 disabled:cursor-not-allowed disabled:bg-surface-100-900 disabled:text-surface-950-50 disabled:opacity-100 w-80"
        type="text"
        bind:value={qbtUsername}
        disabled={data.settings.qbt_username.env_override}
      />
      {#if data.settings.qbt_username.env_override}{@render envChip()}{/if}
    </label>
    <label class="label">
      <span class="label-text flex items-center gap-2">
        Password
      </span>
      <!-- Need autocomplete="new-password" to prevent password manager from trying to save the password -->
      <input
        class="input border border-surface-600 bg-surface-50-950 text-surface-950-50 placeholder:text-black/40 dark:placeholder:text-white/40 disabled:cursor-not-allowed disabled:bg-surface-100-900 disabled:text-surface-950-50 disabled:opacity-100 w-80"
        type="password"
        bind:value={qbtPassword}
        disabled={data.settings.qbt_password.env_override}
        autocomplete="new-password"
      />
      {#if data.settings.qbt_password.env_override}{@render envChip()}{/if}
    </label>
    <div class="flex flex-col">
      <span class="label-text flex items-center gap-2 mb-1">
        Path Mapping
      </span>
      <div class="flex items-center gap-2">
        <input
          class="input border border-surface-600 bg-surface-50-950 text-surface-950-50 placeholder:text-black/40 dark:placeholder:text-white/40 disabled:cursor-not-allowed disabled:bg-surface-100-900 disabled:text-surface-950-50 disabled:opacity-100 w-96"
          type="text"
          bind:value={qbtPathLocal}
          disabled={data.settings.qbt_path_local.env_override}
        />
        <span class="font-bold">→</span>
        <input
          class="input border border-surface-600 bg-surface-50-950 text-surface-950-50 placeholder:text-black/40 dark:placeholder:text-white/40 disabled:cursor-not-allowed disabled:bg-surface-100-900 disabled:text-surface-950-50 disabled:opacity-100 w-96"
          type="text"
          bind:value={qbtPathRemote}
          disabled={data.settings.qbt_path_remote.env_override}
        />
      </div>
      {#if data.settings.qbt_path_local.env_override || data.settings.qbt_path_remote.env_override}{@render envChip()}{/if}
    </div>
    <label class="label">
      <span class="label-text flex items-center gap-2">
        Category
      </span>
      <input
        class="input border border-surface-600 bg-surface-50-950 text-surface-950-50 placeholder:text-black/40 dark:placeholder:text-white/40 disabled:cursor-not-allowed disabled:bg-surface-100-900 disabled:text-surface-950-50 disabled:opacity-100 w-80"
        type="text"
        bind:value={qbtCategory}
        disabled={data.settings.qbt_category.env_override}
      />
      {#if data.settings.qbt_category.env_override}{@render envChip()}{/if}
    </label>
    <label class="label">
      <span class="label-text flex items-center gap-2">
        Download Location
      </span>
      <input
        class="input border border-surface-600 bg-surface-50-950 text-surface-950-50 placeholder:text-black/40 dark:placeholder:text-white/40 disabled:cursor-not-allowed disabled:bg-surface-100-900 disabled:text-surface-950-50 disabled:opacity-100 w-80"
        type="text"
        bind:value={qbtDownloadLocation}
        disabled={data.settings.qbt_download_location.env_override}
      />
      {#if data.settings.qbt_download_location.env_override}{@render envChip()}{/if}
    </label>
    <label class="label w-fit">
      <span class="label-text flex items-center gap-2">
        Polling Rate (s)
      </span>
      <input
        class="input border border-surface-600 bg-surface-50-950 text-surface-950-50 placeholder:text-black/40 dark:placeholder:text-white/40 disabled:cursor-not-allowed disabled:bg-surface-100-900 disabled:text-surface-950-50 disabled:opacity-100 w-24"
        type="number"
        min="5"
        bind:value={qbtPollingRate}
        disabled={data.settings.qbt_polling_rate.env_override}
      />
      {#if data.settings.qbt_polling_rate.env_override}{@render envChip()}{/if}
    </label>
  </section>

  <button type="button" onclick={saveSettings} disabled={saving} class="btn preset-filled-primary-500 w-fit">
    {saving ? 'Saving…' : 'Save'}
  </button>
</form>
