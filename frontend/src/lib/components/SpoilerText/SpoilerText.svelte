<script lang="ts">
  import type { Snippet } from "svelte";

  let { children }: { children: Snippet } = $props();
</script>

<span class="spoiler:bg-foreground spoiler:text-transparent spoiler:select-none rounded-sm transition-colors">
  {@render children()}
</span>
