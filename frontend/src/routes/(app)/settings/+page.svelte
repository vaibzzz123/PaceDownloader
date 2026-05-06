<script lang="ts">
  import { PUBLIC_BACKEND_URL } from '$env/static/public';
  import AlertTriangleIcon from "@lucide/svelte/icons/alert-triangle";
  import type { PageProps } from "./$types";

  let { data }: PageProps = $props();

  let form = $state({
    media_data_location: (data.settings.media_data_location.value as string) ?? '',
    prefer_extended: Boolean(data.settings.prefer_extended.value),
    qbt_hostname: (data.settings.qbt_hostname.value as string) ?? '',
    qbt_username: (data.settings.qbt_username.value as string) ?? '',
    qbt_password: (data.settings.qbt_password.value as string) ?? '',
    qbt_path_local: (data.settings.qbt_path_local.value as string) ?? '',
    qbt_path_remote: (data.settings.qbt_path_remote.value as string) ?? '',
    qbt_category: (data.settings.qbt_category.value as string) ?? '',
    qbt_download_location: (data.settings.qbt_download_location.value as string) ?? '',
    qbt_polling_rate: (data.settings.qbt_polling_rate.value as number) ?? 8,
    log_level: (data.settings.log_level.value as string) ?? 'INFO',
  });

  // Need to do things this way so that the form is updated when the page is reloaded
  // TODO: Find a better way to do all of this, feels way too hacky for something relatively simple
  $effect(() => {
    form.media_data_location = (data.settings.media_data_location.value as string) ?? '';
    form.prefer_extended = Boolean(data.settings.prefer_extended.value);
    form.qbt_hostname = (data.settings.qbt_hostname.value as string) ?? '';
    form.qbt_username = (data.settings.qbt_username.value as string) ?? '';
    form.qbt_password = (data.settings.qbt_password.value as string) ?? '';
    form.qbt_path_local = (data.settings.qbt_path_local.value as string) ?? '';
    form.qbt_path_remote = (data.settings.qbt_path_remote.value as string) ?? '';
    form.qbt_category = (data.settings.qbt_category.value as string) ?? '';
    form.qbt_download_location = (data.settings.qbt_download_location.value as string) ?? '';
    form.qbt_polling_rate = (data.settings.qbt_polling_rate.value as number) ?? 8;
    form.log_level = (data.settings.log_level.value as string) ?? 'INFO';
  });

  let saveError = $state<string | null>(null);
  let saving = $state(false);
  let saved = $state(false);

  async function saveSettings() {
    saving = true;
    saveError = null;
    saved = false;
    try {
      const res = await fetch(`${PUBLIC_BACKEND_URL}/settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          media_data_location: form.media_data_location,
          prefer_extended: form.prefer_extended,
          qbt_hostname: form.qbt_hostname,
          qbt_username: form.qbt_username,
          qbt_password: form.qbt_password,
          qbt_path_local: form.qbt_path_local || null,
          qbt_path_remote: form.qbt_path_remote || null,
          qbt_category: form.qbt_category || null,
          qbt_download_location: form.qbt_download_location || null,
          qbt_polling_rate: form.qbt_polling_rate,
          log_level: form.log_level,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        saveError = body.detail ?? 'Failed to save settings';
      } else {
        saved = true;
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
        class="input w-80"
        type="text"
        bind:value={form.media_data_location}
        disabled={data.settings.media_data_location.env_override}
      />
      {#if data.settings.media_data_location.env_override}{@render envChip()}{/if}
    </label>
    <label class="label w-fit">
      <span class="label-text flex items-center gap-2">
        Prefer Extended
      </span>
      <input
        class="checkbox"
        type="checkbox"
        bind:checked={form.prefer_extended}
        disabled={data.settings.prefer_extended.env_override}
      />
      {#if data.settings.prefer_extended.env_override}{@render envChip()}{/if}
    </label>
    <label class="label w-fit">
      <span class="label-text flex items-center gap-2">
        Log Level
      </span>
      <select class="select pl-3" bind:value={form.log_level} disabled={data.settings.log_level.env_override}>
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
        class="input w-80"
        type="text"
        bind:value={form.qbt_hostname}
        disabled={data.settings.qbt_hostname.env_override}
      />
      {#if data.settings.qbt_hostname.env_override}{@render envChip()}{/if}
    </label>
    <label class="label">
      <span class="label-text flex items-center gap-2">
        Username
      </span>
      <input
        class="input w-80"
        type="text"
        bind:value={form.qbt_username}
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
        class="input w-80"
        type="password"
        bind:value={form.qbt_password}
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
          class="input w-96"
          type="text"
          bind:value={form.qbt_path_local}
          disabled={data.settings.qbt_path_local.env_override}
        />
        <span class="font-bold">→</span>
        <input
          class="input w-96"
          type="text"
          bind:value={form.qbt_path_remote}
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
        class="input w-80"
        type="text"
        bind:value={form.qbt_category}
        disabled={data.settings.qbt_category.env_override}
      />
      {#if data.settings.qbt_category.env_override}{@render envChip()}{/if}
    </label>
    <label class="label">
      <span class="label-text flex items-center gap-2">
        Download Location
      </span>
      <input
        class="input w-80"
        type="text"
        bind:value={form.qbt_download_location}
        disabled={data.settings.qbt_download_location.env_override}
      />
      {#if data.settings.qbt_download_location.env_override}{@render envChip()}{/if}
    </label>
    <label class="label w-fit">
      <span class="label-text flex items-center gap-2">
        Polling Rate (s)
      </span>
      <input
        class="input w-24"
        type="number"
        min="5"
        bind:value={form.qbt_polling_rate}
        disabled={data.settings.qbt_polling_rate.env_override}
      />
      {#if data.settings.qbt_polling_rate.env_override}{@render envChip()}{/if}
    </label>
  </section>

  <button type="button" onclick={saveSettings} disabled={saving} class="btn preset-filled-primary-500 w-fit">
    {saving ? 'Saving…' : 'Save'}
  </button>
</form>
