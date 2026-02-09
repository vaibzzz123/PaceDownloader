<script lang="ts">
	import SeasonGrid from '$lib/components/SeasonGrid/SeasonGrid.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<SeasonGrid seasons={data.seasons} />