<script>
  import "../app.css";
  import { appState } from "$lib/state/index.svelte";
  import LeftSideMenu from "$lib/components/LeftSideMenuSkeleton/LeftSideMenuSkeleton.svelte";

  let { children } = $props();

  $effect(() => {
    document.documentElement.classList.toggle("dark", appState.darkMode);
    document.documentElement.classList.toggle("spoiler", appState.spoilerMode);
  });
</script>

<div class="grid grid-cols-[auto_1fr]">
  <aside class="sticky top-0  h-screen py-4 px-2">
    <LeftSideMenu />
  </aside>
  <main class="col-span-1 p-4 space-y-4">
    {@render children()}
  </main>
</div>
