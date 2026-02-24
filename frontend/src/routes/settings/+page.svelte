<script lang="ts">
  import AlertTriangleIcon from "@lucide/svelte/icons/alert-triangle";


  const settings = $state({
    media_data_location: { value: "asdds", is_env_var: false },
    prefer_extended: { value: true, is_env_var: false },
    qbt_hostname: { value: "asdds", is_env_var: true },
    qbt_username: { value: "asdds", is_env_var: true },
    qbt_password: { value: "asdds", is_env_var: true },
    qbt_path_here: { value: "/path_from_here", is_env_var: true },
    qbt_path_qbt: { value: "/path_from_qbt", is_env_var: true },
    qbt_category: { value: "asdds", is_env_var: false },
    qbt_download_location: { value: "asdds", is_env_var: true },
    qbt_polling_rate: { value: 10, is_env_var: false },
    log_level: { value: "INFO", is_env_var: false },
  });
</script>

{#snippet envBadge()}
  <!-- <span class="chip bg-orange-500/15 dark:bg-orange-400/20 hover:bg-orange-500/25 dark:hover:bg-orange-400/30 text-orange-700 dark:text-orange-300 text-xs font-mono"></span> -->
{/snippet}

{#snippet envChip()}
<span class="preset-tonal-warning mt-2 w-fit text-xs inline-flex items-center gap-2 rounded py-1 px-3 transition-all hover:brightness-90">
  <AlertTriangleIcon size={15}/><p>Set via environment variable — remove it to edit this setting.</p>
</span>
{/snippet}

<h1 class="-mt-2 text-2xl font-bold">Settings</h1>
<form class="flex flex-col gap-6">

  <section class="flex flex-col gap-3">
    <h2 class="text-lg font-semibold">General</h2>
    <label class="label">
      <span class="label-text flex items-center gap-2">
        Media Data Location
        {#if settings.media_data_location.is_env_var}{@render envBadge()}{/if}
      </span>
      <input
        class="input w-80"
        type="text"
        bind:value={settings.media_data_location.value}
        disabled={settings.media_data_location.is_env_var}
      />
      {#if settings.media_data_location.is_env_var}{@render envChip()}{/if}
    </label>
    <label class="label w-fit">
      <span class="label-text flex items-center gap-2">
        Prefer Extended
        {#if settings.prefer_extended.is_env_var}{@render envBadge()}{/if}
      </span>
      <input
        class="checkbox"
        type="checkbox"
        bind:checked={settings.prefer_extended.value}
        disabled={settings.prefer_extended.is_env_var}
      />
      {#if settings.prefer_extended.is_env_var}{@render envChip()}{/if}
    </label>
    <label class="label w-fit">
      <span class="label-text flex items-center gap-2">
        Log Level
        {#if settings.log_level.is_env_var}{@render envBadge()}{/if}
      </span>
      <select class="select pl-3" bind:value={settings.log_level.value} disabled={settings.log_level.is_env_var}>
        <option value="DEBUG">DEBUG</option>
        <option value="INFO">INFO</option>
        <option value="WARNING">WARNING</option>
        <option value="ERROR">ERROR</option>
      </select>
      {#if settings.log_level.is_env_var}{@render envChip()}{/if}
    </label>
  </section>

  <section class="flex flex-col gap-3">
    <h2 class="text-lg font-semibold">qBittorrent</h2>
    <label class="label">
      <span class="label-text flex items-center gap-2">
        Hostname
        {#if settings.qbt_hostname.is_env_var}{@render envBadge()}{/if}
      </span>
      <input
        class="input w-80"
        type="text"
        bind:value={settings.qbt_hostname.value}
        disabled={settings.qbt_hostname.is_env_var}
      />
      {#if settings.qbt_hostname.is_env_var}{@render envChip()}{/if}
    </label>
    <label class="label">
      <span class="label-text flex items-center gap-2">
        Username
        {#if settings.qbt_username.is_env_var}{@render envBadge()}{/if}
      </span>
      <input
        class="input w-80"
        type="text"
        bind:value={settings.qbt_username.value}
        disabled={settings.qbt_username.is_env_var}
      />
      {#if settings.qbt_username.is_env_var}{@render envChip()}{/if}
    </label>
    <label class="label">
      <span class="label-text flex items-center gap-2">
        Password
        {#if settings.qbt_password.is_env_var}{@render envBadge()}{/if}
      </span>
      <!-- Need autocomplete="new-password" to prevent password manager from trying to save the password -->
      <input
        class="input w-80"
        type="password"
        bind:value={settings.qbt_password.value}
        disabled={settings.qbt_password.is_env_var}
        autocomplete="new-password"
      />
      {#if settings.qbt_password.is_env_var}{@render envChip()}{/if}
    </label>
    <div class="flex flex-col">
      <span class="label-text flex items-center gap-2 mb-1">
        Path Mapping
        {#if settings.qbt_path_here.is_env_var}{@render envBadge()}{/if}
      </span>
      <div class="flex items-center gap-2">
        <input
          class="input w-96"
          type="text"
          bind:value={settings.qbt_path_here.value}
          disabled={settings.qbt_path_here.is_env_var}
        />
        <span class="font-bold">:</span>
        <input
          class="input w-96"
          type="text"
          bind:value={settings.qbt_path_qbt.value}
          disabled={settings.qbt_path_qbt.is_env_var}
        />
      </div>
      {#if settings.qbt_path_here.is_env_var}{@render envChip()}{/if}
    </div>
    <label class="label">
      <span class="label-text flex items-center gap-2">
        Category
        {#if settings.qbt_category.is_env_var}{@render envBadge()}{/if}
      </span>
      <input
        class="input w-80"
        type="text"
        bind:value={settings.qbt_category.value}
        disabled={settings.qbt_category.is_env_var}
      />
      {#if settings.qbt_category.is_env_var}{@render envChip()}{/if}
    </label>
    <label class="label">
      <span class="label-text flex items-center gap-2">
        Download Location
        {#if settings.qbt_download_location.is_env_var}{@render envBadge()}{/if}
      </span>
      <input
        class="input w-80"
        type="text"
        bind:value={settings.qbt_download_location.value}
        disabled={settings.qbt_download_location.is_env_var}
      />
      {#if settings.qbt_download_location.is_env_var}{@render envChip()}{/if}
    </label>
    <label class="label w-fit">
      <span class="label-text flex items-center gap-2">
        Polling Rate (s)
        {#if settings.qbt_polling_rate.is_env_var}{@render envBadge()}{/if}
      </span>
      <input
        class="input w-24"
        type="number"
        bind:value={settings.qbt_polling_rate.value}
        disabled={settings.qbt_polling_rate.is_env_var}
      />
      {#if settings.qbt_polling_rate.is_env_var}{@render envChip()}{/if}
    </label>
  </section>

  <button type="button" onclick={() => console.log(settings)} class="btn preset-filled-primary-500 w-fit">Save</button>
</form>
