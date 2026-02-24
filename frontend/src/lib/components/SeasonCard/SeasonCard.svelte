<script lang="ts">
  let { title, image, num, gridMode } = $props();
</script>

<div
  class="card preset-filled-primary-500 overflow-hidden {gridMode
    ? 'transition-transform hover:scale-105'
    : ''}"
>
  <a
    href={`/season/${num}`}
    class="overflow-hidden block rounded-t-xl relative isolate {gridMode ? '' : 'pointer-events-none'}"
  >
    <img
      src={image}
      alt={title}
      class="h-auto {gridMode ? 'max-h-100' : 'max-h-100'}"
    />
    <div class="hidden spoiler:block absolute inset-0 backdrop-blur-md"></div>
  </a>
  <div class="justify-center py-3 w-0 min-w-full h5 text-center text-wrap">
    <span class="spoiler:hidden">{title}</span>
    <span class="hidden spoiler:inline">Season {num}</span>
  </div>
</div>
