<script lang="ts">
  import SpoilerText from "$lib/components/SpoilerText/SpoilerText.svelte";
  import DownloadIcon from "@lucide/svelte/icons/download";
  import PauseIcon from "@lucide/svelte/icons/pause";
  import PlayIcon from "@lucide/svelte/icons/play";
  import Trash2Icon from "@lucide/svelte/icons/trash-2";

  let {data = [], spoilerName = true, headerMappings = {}, actionsColumn = false, hiddenColumns = []} = $props();

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
  const keys = $derived(Object.keys(data[0] || {}));

  function headerLabel(key: string) {
    const label = headerMappings[key] || key;
    return label.charAt(0).toUpperCase() + label.slice(1);
  }

  let isDownloadRunning = $state(false);
</script>

<div class="table-wrap">
  <table class="table">
    <thead>
      <tr>
        {#each keys as key (key)}
          {#if !hiddenColumns.includes(key)}
            <th class="text-black dark:text-white">{headerLabel(key)}</th>
          {/if}
        {/each}
        {#if actionsColumn}
          <th class="text-black dark:text-white">Actions</th>
        {/if}
      </tr>
    </thead>
    <tbody>
      {#each data as item, i (i)}
      {@const rowStyle = statusStyle(item.status)}
        <tr class="h-13 {rowStyle?.bg ?? ''} {rowStyle?.hover ?? 'hover:bg-black/10 dark:hover:bg-white/10'}">
          {#each keys as key (key)}
          {#if !hiddenColumns.includes(key)}
            {#if key === 'title' && spoilerName}
              <td><SpoilerText>{item[key]}</SpoilerText></td>
            {:else}
              <td>{item[key]}</td>
            {/if}
          {/if}
          {/each}
          {#if actionsColumn}
            <td>
              <!-- Temporary isDownloadRunning variable for previewing, will be dynamic once properly built -->
              <button class="btn-icon" disabled={isDownloadRunning}><DownloadIcon /></button>
              <button class="btn-icon" onclick={() => isDownloadRunning = !isDownloadRunning}>{#if isDownloadRunning}<PauseIcon/>{:else}<PlayIcon/>{/if}</button>
              <button class="btn-icon"><Trash2Icon /></button>
            </td>
          {/if}
        </tr>
      {/each}
    </tbody>
  </table>
</div>