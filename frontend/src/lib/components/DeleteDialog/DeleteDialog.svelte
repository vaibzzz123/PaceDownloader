<script lang="ts">
  import type { Snippet } from 'svelte';
  import type { HTMLButtonAttributes } from 'svelte/elements';
  import XIcon from '@lucide/svelte/icons/x';
  import { Dialog, Portal } from '@skeletonlabs/skeleton-svelte';

  let { button, messageSnippet, message = 'Are you sure? This cannot be undone.', onConfirm, disabled = false }: {
    button: Snippet<[HTMLButtonAttributes]>;
    messageSnippet?: Snippet;
    message?: string;
    onConfirm: () => void;
    disabled?: boolean;
  } = $props();

  const animation =
    'transition transition-discrete opacity-0 translate-y-[100px] starting:data-[state=open]:opacity-0 starting:data-[state=open]:translate-y-[100px] data-[state=open]:opacity-100 data-[state=open]:translate-y-0';
</script>

<Dialog>
  {#if disabled}
    {@render button({ disabled })}
  {:else}
    <Dialog.Trigger element={button} />
  {/if}
  <Portal>
    <Dialog.Backdrop class="fixed inset-0 z-50 bg-surface-50-950/50" />
    <Dialog.Positioner class="fixed inset-0 z-50 flex justify-center items-center p-4">
      <Dialog.Content class="card bg-surface-100-900 w-full max-w-sm p-4 space-y-4 shadow-xl {animation}">
        <header class="flex justify-between items-center">
          <Dialog.Title class="text-lg font-bold">Confirm Delete</Dialog.Title>
          <Dialog.CloseTrigger class="btn-icon hover:preset-tonal">
            <XIcon class="size-4" />
          </Dialog.CloseTrigger>
        </header>
        <Dialog.Description class="text-sm">
          {#if messageSnippet}
            {@render messageSnippet()}
          {:else}
            {message}
          {/if}
        </Dialog.Description>
        <footer class="flex justify-end gap-2">
          <Dialog.CloseTrigger class="btn preset-tonal">Cancel</Dialog.CloseTrigger>
          <Dialog.CloseTrigger class="btn preset-filled-error-500" onclick={onConfirm}>Delete</Dialog.CloseTrigger>
        </footer>
      </Dialog.Content>
    </Dialog.Positioner>
  </Portal>
</Dialog>
