<script>
	import '../app.css';
	import { appState } from '$lib/state/index.svelte';
  import LeftSideMenu from '$lib/components/LeftSideMenu/LeftSideMenu.svelte';

	let { children } = $props();

	$effect(() => {
		document.documentElement.classList.toggle('dark', appState.darkMode);
		document.documentElement.classList.toggle('spoiler', appState.spoilerMode);
	});
</script>

<div class="fixed top-0 left-0 z-40 p-2 m-auto">
	<LeftSideMenu />
</div>

<main class="pt-12">
	{@render children()}
</main>
