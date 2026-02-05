<script lang="ts">
  import type { Snippet } from "svelte";

  let { children }: { children: Snippet } = $props();
</script>

<span class="spoiler:bg-surface-950 dark:spoiler:bg-surface-200 spoiler:text-transparent spoiler:select-none rounded-sm transition-colors">
  {@render children()}
</span>
