<script lang="ts">
  import type { Snippet } from "svelte";
  import SearchIcon from "@lucide/svelte/icons/search";
  import Fuse from "fuse.js";

  let {
    data = [],
    header,
    row,
    searchBox,
    searchableFields,
    highlightId,
    idKey,
  }: {
    data: any[];
    header: Snippet;
    row: Snippet<[any]>;
    searchBox: boolean;
    searchableFields?: string[];
    highlightId?: string;
    idKey?: string;
  } = $props();

  function statusStyle(status: string) {
    const colors: Record<string, { bg: string; hover: string }> = {
      Hardlinked: { bg: "bg-green-500/20", hover: "hover:bg-green-500/30" },
      Copied: { bg: "bg-green-500/20", hover: "hover:bg-green-500/30" },
      Completed: { bg: "bg-green-500/20", hover: "hover:bg-green-500/30" },
      Downloading: { bg: "bg-purple-500/20", hover: "hover:bg-purple-500/30" },
      Paused: { bg: "bg-yellow-500/20", hover: "hover:bg-yellow-500/30" },
      "Download Complete": {
        bg: "bg-blue-500/20",
        hover: "hover:bg-blue-500/30",
      },
      Error: { bg: "bg-red-500/20", hover: "hover:bg-red-500/30" },
    };
    return colors[status] ?? null;
  }

  const fuse = $derived(
    new Fuse(data, {
      keys: searchableFields || [],
      // Play with this number to adjust search sensitivity (0.0 = exact match, 1.0 = match anything)
      threshold: 0.3,
      // Resolve values ourselves so we see raw types (bool, number) before stringification
      getFn: (obj: Record<string, unknown>, path: string | string[]) => {
        const keys = Array.isArray(path) ? path : path.split(".");
        let value: unknown = obj;
        for (const key of keys) {
          if (value == null) return "";
          value = (value as Record<string, unknown>)[key];
        }
        const toDisplayString = (v: unknown): string => {
          if (typeof v === "boolean") return v ? "Yes" : "No";
          return v != null ? String(v) : "";
        };
        if (Array.isArray(value)) return value.map(toDisplayString);
        return toDisplayString(value);
      },
    }),
  );

  let searchQuery = $state("");
  let filteredData = $derived(
    searchQuery ? fuse.search(searchQuery).map((result) => result.item) : data,
  );

  $effect.pre(() => {});

function highlight(node: HTMLTableRowElement, shouldHighlight: boolean) {
  if (!shouldHighlight) return;

  node.scrollIntoView({ behavior: 'smooth', block: 'center' });

  const transitionClasses = ['transition-all', 'duration-300'];
  const effectClasses = [
    'ring-2',
    'ring-white/60',
    'dark:ring-white/40',
    'ring-inset',
    'brightness-150',
    'saturate-300',
    'shadow-lg',
    'z-10',
    'relative'
  ];

  node.classList.add(...transitionClasses, ...effectClasses);
  setTimeout(() => {
    node.classList.remove(...effectClasses);
  }, 1500);

  // Remove transition classes after a delay so transition effects
  // don't persist after highlight is removed
  setTimeout(() => {
    node.classList.remove(...transitionClasses);
  }, 1750);
}








</script>

<!-- I hate this, but apparently the way to override Tailwind's table padding is to use :global() -->
<!-- Or apply it everywhere td and th is being used (in parents) which adds too much extra work -->
<!-- TODO: Figure out a better way to do this -->
<style>
  :global(.table td),
  :global(.table th) {
    padding-left: 0.75rem;  /* Tailwind px-3 */
    padding-right: 0.75rem;
  }

  :global(.table td:first-child),
  :global(.table th:first-child) {
    padding-left: 1rem;  /* Tailwind pl-4 */
  }

  :global(.table td:last-child),
  :global(.table th:last-child) {
    padding-right: 1rem;  /* Tailwind pr-4 */
  }
</style>

<div>
  {#if searchBox}
    <!-- TODO: experiment with adding max-w-xs below for compacted search box, whatever looks better -->
    <div class="relative mb-3">
      <SearchIcon
        size={16}
        class="absolute left-3 top-1/4 pointer-events-none"
      />
      <input
        class="input pl-9 placeholder:text-black/40 dark:placeholder:text-white/40"
        type="text"
        bind:value={searchQuery}
        placeholder="Search"
      />
    </div>
  {/if}
  <div class="table-wrap rounded-lg overflow-hidden">
    <!-- TODO: Add resizable table columns down the line -->
    <table class="table">
      <thead>
        <tr class="text-black dark:text-white">
          {@render header()}
        </tr>
      </thead>
      <tbody>
        {#each filteredData as item, i (i)}
          {@const rowStyle = statusStyle(item.status)}
          {@const shouldHighlight =
            highlightId != null &&
            idKey != null &&
            String(item[idKey]) === highlightId}
          <tr
            class="h-13 {rowStyle?.bg ?? ''} {rowStyle?.hover ??
              'hover:bg-black/10 dark:hover:bg-white/10'}"
            use:highlight={shouldHighlight}
          >
            {@render row(item)}
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>
