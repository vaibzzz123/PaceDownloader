<script lang="ts">
  import * as Table from "../ui/table";
  let { episodes, season } = $props();
</script>

<Table.Root>
  <Table.Header>
    <Table.Row>
      <Table.Head>Season</Table.Head>
      <Table.Head>Episode</Table.Head>
      <Table.Head>Name</Table.Head>
      <Table.Head>Duration</Table.Head>
      <Table.Head>Downloaded</Table.Head>
    </Table.Row>
  </Table.Header>
  <Table.Body>
    {#each episodes as episode}
      <Table.Row>
        <Table.Cell>{season}</Table.Cell>
        <Table.Cell>{episode.number}</Table.Cell>
        <Table.Cell>{episode.title}</Table.Cell>
        <Table.Cell>{episode.duration}</Table.Cell>
        <Table.Cell>{episode.downloaded ? 'Yes' : 'No'}</Table.Cell>
      </Table.Row>
    {/each}
  </Table.Body>
</Table.Root>