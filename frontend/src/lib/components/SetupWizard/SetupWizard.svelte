<script lang="ts">
  import ArrowLeftIcon from '@lucide/svelte/icons/arrow-left';
  import ArrowRightIcon from '@lucide/svelte/icons/arrow-right';
  import CheckIcon from '@lucide/svelte/icons/check';
  import { Steps } from '@skeletonlabs/skeleton-svelte';

  type Step = {
    id: string;
    title: string;
    description: string;
  };

  const steps = [
    {
      id: 'welcome',
      title: 'Welcome',
      description: 'Start the PaceDownloader setup flow.',
    },
    {
      id: 'media',
      title: 'Media',
      description: 'Choose where Jellyfin will read One Pace episodes from.',
    },
    {
      id: 'qbt',
      title: 'qBittorrent',
      description: 'Connect PaceDownloader to the qBittorrent Web UI.',
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

  let step = $state(0);

  const isFinalStep = $derived(step === steps.length);

  const hasPlaceholderFields = (id: StepId) => id !== 'welcome';
</script>

<section class="mx-auto flex w-full max-w-4xl flex-col gap-6">
  <header class="flex flex-col gap-1">
    <p class="text-sm font-medium text-surface-600-400">Initial setup</p>
    <h1 class="text-2xl font-bold">Configure PaceDownloader</h1>
  </header>

  <Steps
    {step}
    count={steps.length}
    onStepChange={(details) => (step = details.step)}
    class="w-full"
  >
    <Steps.List class="mb-6 overflow-x-auto pb-2">
      {#each steps as item, index (item.id)}
        <Steps.Item {index}>
          <Steps.Trigger class="gap-2">
            <Steps.Indicator>{index + 1}</Steps.Indicator>
            <span class="hidden text-sm font-medium sm:inline">{item.title}</span>
          </Steps.Trigger>
          {#if index < steps.length - 1}
            <Steps.Separator />
          {/if}
        </Steps.Item>
      {/each}
    </Steps.List>

    <div class="card bg-surface-100-900 p-5">
      {#each steps as item, index (item.id)}
        <Steps.Content {index} class="min-h-64">
          <div class="flex flex-col gap-4">
            <div>
              <h2 class="text-xl font-semibold">{item.title}</h2>
              <p class="text-sm text-surface-600-400">{item.description}</p>
            </div>

            {#if hasPlaceholderFields(item.id)}
              <div class="rounded border border-surface-200-800 p-4 text-sm text-surface-600-400">
                {item.title} form fields go here.
              </div>
            {/if}
          </div>
        </Steps.Content>
      {/each}

      <Steps.Content index={steps.length} class="min-h-64">
        <div class="flex min-h-64 flex-col items-center justify-center gap-3 text-center">
          <div class="preset-filled-success-500 flex size-12 items-center justify-center rounded-full">
            <CheckIcon class="size-6" />
          </div>
          <div>
            <h2 class="text-xl font-semibold">Setup complete</h2>
            <p class="text-sm text-surface-600-400">PaceDownloader is ready to save these settings.</p>
          </div>
        </div>
      </Steps.Content>
    </div>

    <footer class="mt-4 flex items-center justify-between gap-3">
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
  </Steps>
</section>
