<script lang="ts">
  import SpoilerText from "../SpoilerText/SpoilerText.svelte";
import * as Table from "../ui/table";
  let { episodes, season } = $props();

  function statusStyle(status: string) {
    const colors: Record<string, { bg: string; hover: string }> = {
      'Hardlinked': { bg: 'bg-green-500/20', hover: 'color-mix(in oklch, var(--color-green-500) 50%, transparent)' },
      'Copied': { bg: 'bg-purple-500/20', hover: 'color-mix(in oklch, var(--color-purple-500) 50%, transparent)' },
      'Downloading': { bg: 'bg-yellow-500/20', hover: 'color-mix(in oklch, var(--color-yellow-500) 50%, transparent)' },
    };
    return colors[status] ?? null;
  }
</script>

<Table.Root>
  <Table.Header>
    <Table.Row>
      <Table.Head>Season</Table.Head>
      <Table.Head>Episode</Table.Head>
      <Table.Head>Name</Table.Head>
      <Table.Head>Duration</Table.Head>
      <Table.Head>Status</Table.Head>
    </Table.Row>
  </Table.Header>
  <Table.Body>
    {#each episodes as episode}
      {@const status = statusStyle(episode.status)}
      <Table.Row
        class={status?.bg ?? ''}
        style={status ? `--row-hover: ${status.hover}` : ''}
      >
        <Table.Cell>{season}</Table.Cell>
        <Table.Cell>{episode.number}</Table.Cell>
        <Table.Cell><SpoilerText>{episode.title}</SpoilerText></Table.Cell>
        <Table.Cell>{episode.duration}</Table.Cell>
        <Table.Cell>{episode.status}</Table.Cell>
      </Table.Row>
    {/each}
  </Table.Body>
</Table.Root>
