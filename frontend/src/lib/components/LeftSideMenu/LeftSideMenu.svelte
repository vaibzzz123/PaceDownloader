<script lang="ts">
  import { Button } from "../ui/button";
  import * as Sheet from "../ui/sheet";
  import MenuIcon from "@lucide/svelte/icons/menu";
  import { appState } from "$lib/state/index.svelte";
  let open: boolean = $state(false);
</script>

<Sheet.Root bind:open>
  <Sheet.Trigger>
    {#snippet child({ props })}
      <Button variant="ghost" size="icon" {...props}>
        <MenuIcon class="size-6" />
        <span class="sr-only">Open menu</span>
      </Button>
    {/snippet}
  </Sheet.Trigger>
  <Sheet.Content side="left">
    <Sheet.Header>
      <Sheet.Title class="text-lg font-bold">Pace Downloader</Sheet.Title>
    </Sheet.Header>
    <nav class="flex flex-col gap-2 px-4">
      <a
        href="/"
        class="hover:bg-accent rounded-md px-3 py-2 text-md font-medium transition-colors"
        onclick={() => (open = false)}
      >
        Episodes
      </a>
      <a
        href="/downloads"
        class="hover:bg-accent rounded-md px-3 py-2 text-md font-medium transition-colors"
        onclick={() => (open = false)}
      >
        Downloads
      </a>
      <a
        href="/settings"
        class="hover:bg-accent rounded-md px-3 py-2 text-md font-medium transition-colors"
        onclick={() => (open = false)}
      >
        Settings
      </a>
    </nav>
    <Sheet.Footer>
      <div class="ml-auto flex items-center gap-2">
        <button onclick={() => (appState.darkMode = !appState.darkMode)}>
          {appState.darkMode ? "Light Mode" : "Dark Mode"}
        </button>

        <button onclick={() => (appState.spoilerMode = !appState.spoilerMode)}>
          {appState.spoilerMode ? "Show Spoilers" : "Hide Spoilers"}
        </button>
      </div>
    </Sheet.Footer>
  </Sheet.Content>
</Sheet.Root>
