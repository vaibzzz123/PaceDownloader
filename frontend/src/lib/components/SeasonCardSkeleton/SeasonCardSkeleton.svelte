<script lang="ts">
  let { title, imagePath, seasonNum, gridMode } = $props();
</script>

<div
  class="card preset-filled-primary-500 {gridMode
    ? 'transition-transform hover:scale-105'
    : ''}"
>
  <a
    href={`/season/${seasonNum}`}
    class="overflow-hidden block rounded-t-xl {gridMode ? '' : 'pointer-events-none'}"
  >
    <img
      src={imagePath}
      alt={title}
      class="h-auto {gridMode ? 'max-h-100' : 'max-h-100'} spoiler:blur-md spoiler:scale-110"
    />
  </a>
  <div class="justify-center py-3 w-0 min-w-full h5 text-center text-wrap">
    <span class="spoiler:hidden">{title}</span>
    <span class="hidden spoiler:inline">Season {seasonNum}</span>
  </div>
</div>
