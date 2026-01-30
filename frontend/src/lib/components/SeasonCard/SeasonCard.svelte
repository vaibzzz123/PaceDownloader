<script>
  import * as Card from "../ui/card";

  let { title, imagePath, seasonNum } = $props();
</script>

<Card.Root class="gap-0 py-0 overflow-hidden w-fit px-0">
  <Card.Content class="p-0">
    <a href={`/season/${seasonNum}`}>
      <img src={imagePath} alt={title} class="h-auto rounded-t-xl max-h-100" />
    </a>
  </Card.Content>
  <Card.Footer class="justify-center py-3 w-0 min-w-full">
    <Card.Title class="text-2xl text-center text-wrap">{title}</Card.Title>
  </Card.Footer>
</Card.Root>