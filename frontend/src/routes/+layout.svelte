<script>
	import '../app.css';
	import { appState } from '$lib/state/index.svelte';
  import LeftSideMenu from '$lib/components/LeftSideMenu/LeftSideMenu.svelte';

	let { children } = $props();
	let menuWidth = $state(0);

	$effect(() => {
		document.documentElement.classList.toggle('dark', appState.darkMode);
		document.documentElement.classList.toggle('spoiler', appState.spoilerMode);
	});
</script>

<div class="w-fit p-2" bind:clientWidth={menuWidth}>
	<LeftSideMenu />
</div>
<main class="px-8" style:padding-left="{menuWidth}px">
	{@render children()}
</main>
