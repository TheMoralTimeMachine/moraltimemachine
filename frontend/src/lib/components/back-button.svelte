<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { previousStagePath } from '$lib/stages';
	import Button from '$lib/components/ui/button.svelte';

	const prev = $derived(previousStagePath($page.url.pathname));
</script>

{#if prev}
	<Button variant="outline" onclick={() => goto(prev)}>← Back</Button>
{/if}
