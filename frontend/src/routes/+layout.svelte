<script>
	let { children } = $props();
</script>

<nav>
	<a href="/">Home</a>
</nav>

<main>
	{@render children()}
</main>
