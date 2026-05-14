<script lang="ts">
  import SetupWizard from "$lib/components/SetupWizard/SetupWizard.svelte";

  import type { PageProps } from './$types';

  let { data }: PageProps = $props();
</script>

<main class="flex min-h-screen items-center justify-center px-4 py-8 sm:px-6 lg:px-8">
  <SetupWizard settings={data.settings}/>
</main>
