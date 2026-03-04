<script lang="ts">
  import SeasonCard from "../SeasonCard/SeasonCard.svelte";
  import SpoilerText from "../SpoilerText/SpoilerText.svelte";
  import type { Snippet } from "svelte";

  let { num, title, image, description, actions }: {
    num: string;
    title: string;
    image: string;
    description: string;
    actions?: Snippet;
  } = $props();
</script>

<div class="flex">
  <div class="shrink-0">
    <SeasonCard {title} {image} {num} gridMode={false}/>
  </div>
  <div class="ml-10 min-w-0 overflow-y-auto flex flex-col">
    <h1 class="text-3xl font-bold h1">Description:</h1>
    <p class="text-gray-600 dark:text-gray-400 mt-2"><SpoilerText>{description}</SpoilerText></p>
    {#if actions}
      <div class="flex mt-auto gap-2">
        {@render actions()}
      </div>
    {/if}
  </div>
</div>
