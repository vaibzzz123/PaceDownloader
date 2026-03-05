<script lang="ts">
  import { Progress } from "@skeletonlabs/skeleton-svelte";

  let { value, status }: { value: number; status: string } = $props();

  const colors: Record<string, { track: string; range: string }> = {
    Hardlinked: { track: "bg-green-500/20", range: "bg-green-500" },
    Copied: { track: "bg-green-500/20", range: "bg-green-500" },
    Downloading: { track: "bg-purple-500/20", range: "bg-purple-500" },
    Paused: { track: "bg-yellow-500/20", range: "bg-yellow-500" },
    "Download Complete": { track: "bg-blue-500/20", range: "bg-blue-500" },
    Error: { track: "bg-red-500/20", range: "bg-red-500" },
    Imported: { track: "bg-green-500/20", range: "bg-green-500" },
  };

  const style = $derived(colors[status] ?? null);
</script>

<Progress
  class="grid grid-cols-[auto_1fr] items-center gap-4"
  {value}
  max={100}
>
  <Progress.Label class="w-8 text-sm">{value}%</Progress.Label>
  <Progress.Track class={style?.track}>
    <Progress.Range
      class={style?.range}
    />
  </Progress.Track>
</Progress>
