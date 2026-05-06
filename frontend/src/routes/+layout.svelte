<script lang="ts">
  import "../app.css";
  import { appState } from "$lib/state/index.svelte";

  let { children } = $props();

  $effect(() => {
    document.documentElement.classList.toggle("dark", appState.darkMode);
    document.documentElement.classList.toggle("spoiler", appState.spoilerMode);
  });
</script>

{@render children()}
