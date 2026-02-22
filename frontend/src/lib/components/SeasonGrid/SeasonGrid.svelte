<script lang="ts">
  import SeasonCard from "../SeasonCard/SeasonCard.svelte";

  let { seasons } = $props();
</script>

<div class="flex flex-wrap gap-6">
  {#each seasons as season}
    <SeasonCard {...season} gridMode={true}/>
  {/each}
</div>