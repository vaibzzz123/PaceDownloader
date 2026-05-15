<script lang="ts">
  import ArrowLeftIcon from '@lucide/svelte/icons/arrow-left';
  import ArrowRightIcon from '@lucide/svelte/icons/arrow-right';
  import AlertTriangleIcon from '@lucide/svelte/icons/alert-triangle';
  import CheckIcon from '@lucide/svelte/icons/check';
  import { Steps } from '@skeletonlabs/skeleton-svelte';

  import type { components } from '$lib/types/api';

  type SettingsResponse = components['schemas']['SettingsResponse'];

  type Props = {
    settings: SettingsResponse;
  };

  let { settings }: Props = $props();

  type Step = {
    id: string;
    title: string;
    description: string;
  };

  const steps = [
    {
      id: 'welcome',
      title: 'Welcome',
      description: 'Start the Pace Downloader setup flow.',
    },
    {
      id: 'media',
      title: 'Media',
      description: 'Choose where Jellyfin will read One Pace episodes from.',
    },
    {
      id: 'qbt',
      title: 'qBittorrent',
      description: 'Connect Pace Downloader to the qBittorrent Web UI.',
    },
    {
      id: 'paths',
      title: 'Paths',
      description: 'Map qBittorrent paths to the app filesystem when needed.',
    },
    {
      id: 'preferences',
      title: 'Preferences',
      description: 'Set download and app behavior defaults.',
    },
    {
      id: 'review',
      title: 'Review',
      description: 'Confirm the setup before saving.',
    },
  ] as const satisfies readonly Step[];

  type StepId = (typeof steps)[number]['id'];

  const setupSections = steps.filter((item) => item.id !== 'welcome' && item.id !== 'review');

  let mediaDataLocation = $derived((settings.media_data_location.value as string) ?? '');
  let qbtHostname = $derived((settings.qbt_hostname.value as string) ?? '');
  let qbtUsername = $derived((settings.qbt_username.value as string) ?? '');
  let qbtPassword = $derived((settings.qbt_password.value as string) ?? '');
  let qbtPathLocal = $derived((settings.qbt_path_local.value as string) ?? '');
  let qbtPathRemote = $derived((settings.qbt_path_remote.value as string) ?? '');
  let preferExtended = $derived(Boolean(settings.prefer_extended.value));
  let qbtCategory = $derived((settings.qbt_category.value as string) ?? '');
  let qbtDownloadLocation = $derived((settings.qbt_download_location.value as string) ?? '');
  let qbtPollingRate = $derived((settings.qbt_polling_rate.value as number) ?? 10);
  let logLevel = $derived((settings.log_level.value as string) ?? 'INFO');

  let step = $state(0);

  const isFinalStep = $derived(step === steps.length);
</script>

{#snippet envChip()}
  <span class="preset-tonal-warning inline-flex w-fit items-center gap-2 rounded px-3 py-1 text-xs">
    <AlertTriangleIcon class="size-4" />
    <span>Set via environment variable.</span>
  </span>
{/snippet}

<section class="card bg-surface-100-900 mx-auto flex w-full max-w-244 flex-col gap-6 p-6 shadow-xl sm:p-8">
  <header class="flex flex-col gap-2">
    <p class="text-sm font-medium">Initial setup</p>
    <h1 class="text-2xl font-bold">Configure Pace Downloader</h1>
  </header>

  <Steps
    {step}
    count={steps.length}
    onStepChange={(details) => (step = details.step)}
    class="flex w-full flex-col gap-5"
  >
    <Steps.List class="flex w-full flex-wrap items-center gap-y-2 lg:flex-nowrap">
      {#each steps as item, index (item.id)}
        <Steps.Item {index} class="flex shrink-0 items-center">
          <Steps.Trigger class="btn justify-start gap-1.5 px-1.5 py-1.5 text-sm hover:preset-tonal">
            <Steps.Indicator class="size-6 shrink-0">{index + 1}</Steps.Indicator>
            <span class="font-medium">{item.title}</span>
          </Steps.Trigger>
          {#if index < steps.length - 1}
            <Steps.Separator class="border-surface-950-50/20 mx-2 hidden h-px w-4 border-t lg:block" />
          {/if}
        </Steps.Item>
      {/each}
    </Steps.List>

    <!-- TODO: The styles look...okay for now, but could be improved, come back later -->
    <div class="card bg-surface-50-950/60 border-surface-950-50/20 border p-5 shadow-sm sm:p-6">
      {#each steps as item, index (item.id)}
        <Steps.Content {index} class="min-h-56">
          <div class="flex flex-col gap-4">
            <div class="max-w-2xl">
              <h2 class="text-xl font-semibold">{item.title}</h2>
              <p class="text-sm">{item.description}</p>
            </div>

            {#if item.id === 'welcome'}
              <div class="grid gap-3 sm:grid-cols-2">
                {#each setupSections as section (section.id)}
                  <div class="card bg-surface-100-900 border-surface-950-50/10 border p-4">
                    <h3 class="font-medium">{section.title}</h3>
                    <p class="mt-1 text-sm">{section.description}</p>
                  </div>
                {/each}
              </div>
            {:else if item.id === 'media'}
              <fieldset class="grid gap-4">
                <label class="label">
                  <span class="label-text">Media data location</span>
                  <input
                    class="input border border-surface-600 bg-surface-50-950 text-surface-950-50 placeholder:text-black/40 dark:placeholder:text-white/40 disabled:cursor-not-allowed disabled:bg-surface-100-900 disabled:text-surface-950-50 disabled:opacity-100 w-full max-w-xl"
                    type="text"
                    placeholder="/media/One Pace"
                    bind:value={mediaDataLocation}
                    disabled={settings.media_data_location.env_override}
                  />
                  <span class="text-surface-700-300 text-xs">
                    Path visible to Pace Downloader where organized One Pace files will be placed.
                  </span>
                  {#if settings.media_data_location.env_override}{@render envChip()}{/if}
                </label>
              </fieldset>
            {:else if item.id === 'qbt'}
              <fieldset class="grid gap-4 sm:grid-cols-2">
                <label class="label sm:col-span-2">
                  <span class="label-text">qBittorrent Web UI URL</span>
                  <input
                    class="input border border-surface-600 bg-surface-50-950 text-surface-950-50 placeholder:text-black/40 dark:placeholder:text-white/40 disabled:cursor-not-allowed disabled:bg-surface-100-900 disabled:text-surface-950-50 disabled:opacity-100 w-full max-w-xl"
                    type="url"
                    placeholder="http://localhost:8080"
                    bind:value={qbtHostname}
                    disabled={settings.qbt_hostname.env_override}
                  />
                  <span class="text-surface-700-300 text-xs">
                    URL Pace Downloader uses to reach qBittorrent.
                  </span>
                  {#if settings.qbt_hostname.env_override}{@render envChip()}{/if}
                </label>

                <label class="label">
                  <span class="label-text">qBittorrent username</span>
                  <input
                    class="input border border-surface-600 bg-surface-50-950 text-surface-950-50 placeholder:text-black/40 dark:placeholder:text-white/40 disabled:cursor-not-allowed disabled:bg-surface-100-900 disabled:text-surface-950-50 disabled:opacity-100 w-full"
                    type="text"
                    autocomplete="username"
                    bind:value={qbtUsername}
                    disabled={settings.qbt_username.env_override}
                  />
                  {#if settings.qbt_username.env_override}{@render envChip()}{/if}
                </label>

                <label class="label">
                  <span class="label-text">qBittorrent password</span>
                  <input
                    class="input border border-surface-600 bg-surface-50-950 text-surface-950-50 placeholder:text-black/40 dark:placeholder:text-white/40 disabled:cursor-not-allowed disabled:bg-surface-100-900 disabled:text-surface-950-50 disabled:opacity-100 w-full"
                    type="password"
                    autocomplete="new-password"
                    bind:value={qbtPassword}
                    disabled={settings.qbt_password.env_override}
                  />
                  {#if settings.qbt_password.env_override}{@render envChip()}{/if}
                </label>
              </fieldset>
            {:else if item.id === 'paths'}
              <fieldset class="grid gap-4 sm:grid-cols-2">
                <label class="label">
                  <span class="label-text">Remote path reported by qBittorrent</span>
                  <input
                    class="input border border-surface-600 bg-surface-50-950 text-surface-950-50 placeholder:text-black/40 dark:placeholder:text-white/40 disabled:cursor-not-allowed disabled:bg-surface-100-900 disabled:text-surface-950-50 disabled:opacity-100 w-full"
                    type="text"
                    placeholder="/downloads"
                    bind:value={qbtPathRemote}
                    disabled={settings.qbt_path_remote.env_override}
                  />
                  <span class="text-surface-700-300 text-xs">
                    Path prefix qBittorrent reports for downloaded files.
                  </span>
                  {#if settings.qbt_path_remote.env_override}{@render envChip()}{/if}
                </label>

                <label class="label">
                  <span class="label-text">Path visible to Pace Downloader</span>
                  <input
                    class="input border border-surface-600 bg-surface-50-950 text-surface-950-50 placeholder:text-black/40 dark:placeholder:text-white/40 disabled:cursor-not-allowed disabled:bg-surface-100-900 disabled:text-surface-950-50 disabled:opacity-100 w-full"
                    type="text"
                    placeholder="/data/torrents/downloads"
                    bind:value={qbtPathLocal}
                    disabled={settings.qbt_path_local.env_override}
                  />
                  <span class="text-surface-700-300 text-xs">
                    Matching path prefix Pace Downloader can read.
                  </span>
                  {#if settings.qbt_path_local.env_override}{@render envChip()}{/if}
                </label>
              </fieldset>
            {:else if item.id === 'preferences'}
              <fieldset class="grid gap-4 sm:grid-cols-2">
                <label class="label">
                  <span class="label-text">qBittorrent category</span>
                  <input
                    class="input border border-surface-600 bg-surface-50-950 text-surface-950-50 placeholder:text-black/40 dark:placeholder:text-white/40 disabled:cursor-not-allowed disabled:bg-surface-100-900 disabled:text-surface-950-50 disabled:opacity-100 w-full"
                    type="text"
                    placeholder="onepace"
                    bind:value={qbtCategory}
                    disabled={settings.qbt_category.env_override}
                  />
                  {#if settings.qbt_category.env_override}{@render envChip()}{/if}
                </label>

                <label class="label">
                  <span class="label-text">qBittorrent download location</span>
                  <input
                    class="input border border-surface-600 bg-surface-50-950 text-surface-950-50 placeholder:text-black/40 dark:placeholder:text-white/40 disabled:cursor-not-allowed disabled:bg-surface-100-900 disabled:text-surface-950-50 disabled:opacity-100 w-full"
                    type="text"
                    placeholder="/downloads"
                    bind:value={qbtDownloadLocation}
                    disabled={settings.qbt_download_location.env_override}
                  />
                  {#if settings.qbt_download_location.env_override}{@render envChip()}{/if}
                </label>

                <label class="label w-fit">
                  <span class="label-text">Polling rate</span>
                  <input
                    class="input border border-surface-600 bg-surface-50-950 text-surface-950-50 placeholder:text-black/40 dark:placeholder:text-white/40 disabled:cursor-not-allowed disabled:bg-surface-100-900 disabled:text-surface-950-50 disabled:opacity-100 w-28"
                    type="number"
                    min="5"
                    step="1"
                    bind:value={qbtPollingRate}
                    disabled={settings.qbt_polling_rate.env_override}
                  />
                  <span class="text-surface-700-300 text-xs">Seconds</span>
                  {#if settings.qbt_polling_rate.env_override}{@render envChip()}{/if}
                </label>

                <label class="label w-fit">
                  <span class="label-text">Log level</span>
                  <select
                    class="select border border-surface-600 bg-surface-50-950 text-surface-950-50 placeholder:text-black/40 dark:placeholder:text-white/40 disabled:cursor-not-allowed disabled:bg-surface-100-900 disabled:text-surface-950-50 disabled:opacity-100 w-40"
                    bind:value={logLevel}
                    disabled={settings.log_level.env_override}
                  >
                    <option value="DEBUG">DEBUG</option>
                    <option value="INFO">INFO</option>
                    <option value="WARNING">WARNING</option>
                    <option value="ERROR">ERROR</option>
                  </select>
                  {#if settings.log_level.env_override}{@render envChip()}{/if}
                </label>

                <label class="label w-fit sm:col-span-2">
                  <span class="label-text">Prefer extended releases</span>
                  <input
                    class="checkbox disabled:cursor-not-allowed disabled:opacity-60"
                    type="checkbox"
                    bind:checked={preferExtended}
                    disabled={settings.prefer_extended.env_override}
                  />
                  {#if settings.prefer_extended.env_override}{@render envChip()}{/if}
                </label>
              </fieldset>
            {:else if item.id === 'review'}
              <div class="border-surface-950-50/10 bg-surface-100-900 grid gap-4 rounded border p-4 text-sm sm:grid-cols-2">
                <div>
                  <p class="font-medium">Media data location</p>
                  <p class="text-surface-950-50 break-all">{mediaDataLocation || 'Not set'}</p>
                </div>
                <div>
                  <p class="font-medium">qBittorrent Web UI URL</p>
                  <p class="text-surface-950-50 break-all">{qbtHostname || 'Not set'}</p>
                </div>
                <div>
                  <p class="font-medium">qBittorrent username</p>
                  <p class="text-surface-950-50 break-all">{qbtUsername || 'Not set'}</p>
                </div>
                <div>
                  <p class="font-medium">qBittorrent password</p>
                  <p class="text-surface-950-50">{qbtPassword ? '********' : 'Not set'}</p>
                </div>
                <div>
                  <p class="font-medium">Remote path reported by qBittorrent</p>
                  <p class="text-surface-950-50 break-all">{qbtPathRemote || 'Not set'}</p>
                </div>
                <div>
                  <p class="font-medium">Path visible to Pace Downloader</p>
                  <p class="text-surface-950-50 break-all">{qbtPathLocal || 'Not set'}</p>
                </div>
                <div>
                  <p class="font-medium">qBittorrent category</p>
                  <p class="text-surface-950-50 break-all">{qbtCategory || 'Not set'}</p>
                </div>
                <div>
                  <p class="font-medium">qBittorrent download location</p>
                  <p class="text-surface-950-50 break-all">{qbtDownloadLocation || 'Not set'}</p>
                </div>
                <div>
                  <p class="font-medium">Polling rate</p>
                  <p class="text-surface-950-50">{qbtPollingRate} seconds</p>
                </div>
                <div>
                  <p class="font-medium">Log level</p>
                  <p class="text-surface-950-50">{logLevel}</p>
                </div>
                <div>
                  <p class="font-medium">Prefer extended releases</p>
                  <p class="text-surface-950-50">{preferExtended ? 'Enabled' : 'Disabled'}</p>
                </div>
              </div>
            {/if}
          </div>
        </Steps.Content>
      {/each}

      <Steps.Content index={steps.length} class="min-h-56">
        <div class="flex min-h-56 flex-col items-center justify-center gap-3 text-center">
          <div class="preset-filled-primary-500 flex size-12 items-center justify-center rounded-full">
            <CheckIcon class="size-6" />
          </div>
          <div>
            <h2 class="text-xl font-semibold">Setup complete</h2>
            <p class="text-sm">Pace Downloader is ready to save these settings.</p>
          </div>
        </div>
      </Steps.Content>

      <footer class="mt-5 flex items-center justify-between gap-3">
        <Steps.PrevTrigger class="btn preset-tonal">
          <ArrowLeftIcon class="size-4" />
          <span>Back</span>
        </Steps.PrevTrigger>

        <Steps.NextTrigger class="btn preset-filled-primary-500">
          {#if isFinalStep}
            <CheckIcon class="size-4" />
            <span>Finish</span>
          {:else}
            <span>Next</span>
            <ArrowRightIcon class="size-4" />
          {/if}
        </Steps.NextTrigger>
      </footer>
    </div>
  </Steps>
</section>
