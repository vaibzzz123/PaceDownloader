<script lang="ts">
  import SeasonCard from "../SeasonCardSkeleton/SeasonCardSkeleton.svelte";
  import SpoilerText from "../SpoilerText/SpoilerText.svelte";

  let { seasonNum, title, imagePath, description } = $props();
</script>

<div class="flex justify-between">
  <SeasonCard {title} {imagePath} {seasonNum} gridMode={false}/>
  <div class="ml-10 w-2/3">
    <h1 class="text-3xl font-bold h1">Description:</h1>
    <p class="text-gray-400 mt-2"><SpoilerText>{description}</SpoilerText></p>
  </div>
</div>