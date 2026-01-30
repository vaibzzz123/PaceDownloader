<script>
	import '../app.css';
	import { state } from '$lib/state/index.svelte';

	let { children } = $props();

	$effect(() => {
		document.documentElement.classList.toggle('dark', state.darkMode);
	});
</script>

<nav>
	<button onclick={() => state.darkMode = !state.darkMode}>
		{state.darkMode ? 'Light Mode' : 'Dark Mode'}
	</button>
</nav>

<main>
	{@render children()}
</main>
