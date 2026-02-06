<script lang="ts">
  interface Props {
    highlightId?: string;
  }

  let { highlightId }: Props = $props();
</script>

<div class="table-wrap">
  <table class="table">
    <thead>
      <tr>
        <th>Episode ID</th>
        <th>Name</th>
        <th>Extended</th>
        <th>Status</th>
        <th>Download Progress</th>
        <th>Actions</th>
        <th>Torrent</th>
      </tr>
    </thead>
    <tbody>
      {#each [] as episode}
      <tr>
        <td>1</td>
        <td>Episode 1</td>
        <td>00:00:00</td>
        <td>Downloading</td>
        <td>
          <button>
            <PlayIcon />
          </button>
          <button>
            <PauseIcon />
          </button>
          <button>
            <Trash2Icon />
          </button>
        </td>
      </tr>
      {/each}
    </tbody>
  </table>
</div>
