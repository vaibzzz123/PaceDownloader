<script>
	import '../app.css';
	import { state } from '$lib/state/index.svelte';

	let { children } = $props();

	$effect(() => {
		document.documentElement.classList.toggle('dark', state.darkMode);
		document.documentElement.classList.toggle('spoiler', state.spoilerMode);
	});
</script>

<nav>
	<button onclick={() => state.darkMode = !state.darkMode}>
		{state.darkMode ? 'Light Mode' : 'Dark Mode'}
	</button>

	<button onclick={() => state.spoilerMode = !state.spoilerMode}>
		{state.spoilerMode ? 'Show Spoilers' : 'Hide Spoilers'}
	</button>
</nav>

<main>
	{@render children()}
</main>
