<script>
	import { Button } from '$lib/components/ui/button';
	let count = $state(0);
</script>

<h1>One Pace Jellyfin Web UI</h1>
<p>Clicks: {count}</p>
<Button onclick={() => count++}>Increment</Button>