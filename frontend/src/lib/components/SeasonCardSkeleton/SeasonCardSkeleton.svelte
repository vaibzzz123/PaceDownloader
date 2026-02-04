<script lang="ts">
  let { title, imagePath, seasonNum } = $props();
</script>


<div class="card p-4 ">
    <a href={`/season/${seasonNum}`}>
      <img src={imagePath} alt={title} class="h-auto rounded-t-xl max-h-100 spoiler:blur-md" />
    </a>
    <div class="justify-center py-3 w-0 min-w-full h4 text-center text-wrap">
      <span class="spoiler:hidden">{title}</span>
      <span class="hidden spoiler:inline">Season {seasonNum}</span>
    </div>
</div>