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

  const setupSections = steps.filter((item) => item.id !== 'welcome' && item.id !== 'review');

  let step = $state(0);

  const isFinalStep = $derived(step === steps.length);

  const hasPlaceholderFields = (id: StepId) => id !== 'welcome';
</script>

<!-- TODO: Play with the background colours here and on line 81 (div below the Steps component), colours are...weird in dark mode -->
<section class="card bg-surface-100-900 mx-auto flex w-full max-w-244 flex-col gap-6 p-6 shadow-xl sm:p-8">
  <header class="flex flex-col gap-2">
    <p class="text-sm font-medium">Initial setup</p>
    <h1 class="text-2xl font-bold">Configure PaceDownloader</h1>
  </header>

  <Steps
    {step}
    count={steps.length}
    onStepChange={(details) => (step = details.step)}
    class="flex w-full flex-col gap-5"
  >
    <Steps.List class="flex w-full flex-wrap items-center gap-x-4 gap-y-2 lg:flex-nowrap lg:justify-between">
      {#each steps as item, index (item.id)}
        <Steps.Item {index} class="shrink-0">
          <Steps.Trigger class="btn justify-start gap-2 px-2 py-1.5 text-sm hover:preset-tonal">
            <Steps.Indicator class="size-7 shrink-0">{index + 1}</Steps.Indicator>
            <span class="font-medium">{item.title}</span>
          </Steps.Trigger>
        </Steps.Item>
      {/each}
    </Steps.List>

    <div class="card bg-surface-100-900 border-surface-950-50/20 border p-5 shadow-sm sm:p-6">
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
                  <div class="card bg-surface-200-800 border-surface-950-50/10 border p-4">
                    <h3 class="font-medium">{section.title}</h3>
                    <p class="mt-1 text-sm">{section.description}</p>
                  </div>
                {/each}
              </div>
            {:else if hasPlaceholderFields(item.id)}
              <div class="bg-surface-200-800 border-surface-950-50/10 rounded border p-4 text-sm">
                {item.title} form fields go here.
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
            <p class="text-sm">PaceDownloader is ready to save these settings.</p>
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
