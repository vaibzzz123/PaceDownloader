<script lang="ts">
  import SeasonCard from "../SeasonCardSkeleton/SeasonCardSkeleton.svelte";

  let { seasonNum, title, imagePath, description } = $props();
</script>

<div class="flex justify-between">
  <SeasonCard {title} {imagePath} {seasonNum} />
</div>