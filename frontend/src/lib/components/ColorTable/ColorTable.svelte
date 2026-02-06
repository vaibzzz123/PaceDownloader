<script lang="ts">
  import type { Snippet } from 'svelte';

  let { data = [], header, row }: {
    data: any[];
    header: Snippet;
    row: Snippet<[any]>;
  } = $props();

  function statusStyle(status: string) {
    const colors: Record<string, { bg: string; hover: string }> = {
      'Hardlinked': { bg: 'bg-green-500/20', hover: 'hover:bg-green-500/30' },
      'Copied': { bg: 'bg-green-500/20', hover: 'hover:bg-green-500/30' },
      'Downloading': { bg: 'bg-purple-500/20', hover: 'hover:bg-purple-500/30' },
      'Paused': { bg: 'bg-yellow-500/20', hover: 'hover:bg-yellow-500/30' },
      'Download Complete': { bg: 'bg-blue-500/20', hover: 'hover:bg-blue-500/30' },
      'Error': { bg: 'bg-red-500/20', hover: 'hover:bg-red-500/30' },
    };
    return colors[status] ?? null;
  }
</script>

<div class="table-wrap">
  <table class="table">
    <thead>
      <tr class="text-black dark:text-white">
        {@render header()}
      </tr>
    </thead>
    <tbody>
      {#each data as item, i (i)}
        {@const rowStyle = statusStyle(item.status)}
        <tr class="h-13 {rowStyle?.bg ?? ''} {rowStyle?.hover ?? 'hover:bg-black/10 dark:hover:bg-white/10'}">
          {@render row(item)}
        </tr>
      {/each}
    </tbody>
  </table>
</div>
