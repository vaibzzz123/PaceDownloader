<script lang="ts">
  import MenuIcon from "@lucide/svelte/icons/menu";
  import XIcon from "@lucide/svelte/icons/x";
  import SunIcon from "@lucide/svelte/icons/sun";
  import MoonIcon from "@lucide/svelte/icons/moon";
  import EyeIcon from "@lucide/svelte/icons/eye";
  import EyeOffIcon from "@lucide/svelte/icons/eye-off";
  import { Dialog, Portal } from '@skeletonlabs/skeleton-svelte';
  import { appState } from "$lib/state/index.svelte";

  let open = $state(false);

  const links = [
    { label: 'Episodes', href: '/' },
    { label: 'Downloads', href: '/downloads' },
    { label: 'Settings', href: '/settings' },
  ];

  const animBackdrop = 'transition transition-discrete opacity-0 starting:data-[state=open]:opacity-0 data-[state=open]:opacity-100';
  const animDrawer = 'transition transition-discrete opacity-0 -translate-x-full starting:data-[state=open]:opacity-0 starting:data-[state=open]:-translate-x-full data-[state=open]:opacity-100 data-[state=open]:translate-x-0';
</script>

<Dialog {open} onOpenChange={(details) => (open = details.open)}>
  <Dialog.Trigger class="btn-icon btn-icon-lg hover:preset-tonal">
    <MenuIcon class="size-6" />
    <span class="sr-only">Open menu</span>
  </Dialog.Trigger>
  <Portal>
    <Dialog.Backdrop class="fixed inset-0 z-50 bg-surface-50-950/50 backdrop-blur-sm {animBackdrop}" />
    <Dialog.Positioner class="fixed inset-0 z-50 flex justify-start">
      <Dialog.Content class="h-screen card bg-surface-100-900 w-sm shadow-xl grid grid-rows-[auto_1fr_auto] p-4 gap-4 {animDrawer}">
        <header class="flex justify-between items-center">
          <Dialog.Title class="text-2xl font-bold">Pace Downloader</Dialog.Title>
          <Dialog.CloseTrigger class="btn-icon preset-tonal">
            <XIcon />
          </Dialog.CloseTrigger>
        </header>
        <nav class="flex flex-col gap-2">
          {#each links as link (link.href)}
            <a
              href={link.href}
              class="btn hover:preset-tonal justify-start px-3 py-2 text-md font-medium"
              onclick={() => (open = false)}
            >
              {link.label}
            </a>
          {/each}
        </nav>
        <footer class="flex flex-col gap-2">
          <button class="btn hover:preset-tonal justify-start px-3" onclick={() => (appState.darkMode = !appState.darkMode)}>
            {#if appState.darkMode}
              <SunIcon class="size-4" />
              <span>Light Mode</span>
            {:else}
              <MoonIcon class="size-4" />
              <span>Dark Mode</span>
            {/if}
          </button>
          <button class="btn hover:preset-tonal justify-start px-3" onclick={() => (appState.spoilerMode = !appState.spoilerMode)}>
            {#if appState.spoilerMode}
              <EyeIcon class="size-4" />
              <span>Show Spoilers</span>
            {:else}
              <EyeOffIcon class="size-4" />
              <span>Hide Spoilers</span>
            {/if}
          </button>
        </footer>
      </Dialog.Content>
    </Dialog.Positioner>
  </Portal>
</Dialog>
