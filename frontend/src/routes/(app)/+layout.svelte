<script lang="ts">
  import LeftSideMenu from "$lib/components/LeftSideMenu/LeftSideMenu.svelte";
  import { beforeNavigate, afterNavigate } from "$app/navigation";
  import { SvelteMap } from "svelte/reactivity";

  let { children } = $props();

  const scrollPositions = new SvelteMap<string, number>();

  beforeNavigate(({ from }) => {
    if (from?.url) {
      scrollPositions.set(from.url.pathname + from.url.search, window.scrollY);
    }
  });

  afterNavigate(({ to }) => {
    const key = to?.url ? to.url.pathname + to.url.search : null;
    const saved = key ? scrollPositions.get(key) : undefined;
    if (saved !== undefined) {
      window.scrollTo({ top: saved, behavior: "instant" });
    }
  });
</script>

<div class="grid grid-cols-[auto_1fr]">
  <aside class="sticky top-0 h-screen py-4 px-2">
    <LeftSideMenu />
  </aside>
  <main class="col-span-1 p-4 space-y-4 mx-10 my-4">
    {@render children()}
  </main>
</div>
