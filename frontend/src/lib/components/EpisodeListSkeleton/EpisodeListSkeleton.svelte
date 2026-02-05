<script lang="ts">
  import SpoilerText from "../SpoilerText/SpoilerText.svelte";
  let { episodes, season } = $props();

  function statusStyle(status: string) {
    const colors: Record<string, { bg: string; hover: string }> = {
      'Hardlinked': { bg: 'bg-green-500/20', hover: 'hover:bg-green-500/30' },
      'Copied': { bg: 'bg-purple-500/20', hover: 'hover:bg-purple-500/30' },
      'Downloading': { bg: 'bg-yellow-500/20', hover: 'hover:bg-yellow-500/30' },
    };
    return colors[status] ?? null;
  }

</script>

<div class="table-wrap">
  <table class="table">
    <thead class="text-black dark:text-white">
      <tr>
        <th>Season</th>
        <th>Episode</th>
        <th>Name</th>
        <th>Duration</th>
        <th>Status</th>
      </tr>
    </thead>
    <tbody>
      {#each episodes as episode}
      {@const statusStyles = statusStyle(episode.status)}
        <tr
        class="{statusStyles?.bg ?? ''} {statusStyles?.hover ?? 'hover:bg-black/5 dark:hover:bg-white/10'}"
        >
          <td>{season}</td>
          <td>{episode.number}</td>
          <td><SpoilerText>{episode.title}</SpoilerText></td>
          <td>{episode.duration}</td>
          <td>{episode.status}</td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>
