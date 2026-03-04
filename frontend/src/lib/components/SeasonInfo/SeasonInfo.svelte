<script lang="ts">
  import SeasonCard from "../SeasonCard/SeasonCard.svelte";
  import SpoilerText from "../SpoilerText/SpoilerText.svelte";
  import DownloadIcon from "@lucide/svelte/icons/download";
  import PauseIcon from "@lucide/svelte/icons/pause";
  import PlayIcon from "@lucide/svelte/icons/play";
  import Trash2Icon from "@lucide/svelte/icons/trash-2";

  let { num, title, image, description } = $props();
</script>

<div class="flex">
  <div class="shrink-0">
    <SeasonCard {title} {image} {num} gridMode={false}/>
  </div>
  <div class="ml-10 min-w-0 overflow-y-auto flex flex-col">
    <h1 class="text-3xl font-bold h1">Description:</h1>
    <p class="text-gray-600 dark:text-gray-400 mt-2"><SpoilerText>{description}</SpoilerText></p>
    <div class="flex mt-auto gap-2">
      <button class="btn preset-filled-primary-500 rounded-xl text-sm"><DownloadIcon size={18}/><span>Download All</span></button>
      <button class="btn preset-tonal-warning rounded-xl text-sm"><PauseIcon size={18}/><span>Pause All</span></button>
      <button class="btn preset-tonal-success rounded-xl text-sm"><PlayIcon size={18}/><span>Resume All</span></button>
      <button class="btn preset-tonal-error rounded-xl text-sm"><Trash2Icon size={18}/><span>Delete All</span></button>
    </div>
  </div>
</div>