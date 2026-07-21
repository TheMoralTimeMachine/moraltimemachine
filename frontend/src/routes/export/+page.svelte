<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { session } from '$lib/stores/session.svelte';
	import { reflectionsComplete } from '$lib/stages';
	import Button from '$lib/components/ui/button.svelte';
	import ReportPreview from '$lib/components/report-preview.svelte';
	import BackButton from '$lib/components/back-button.svelte';
	import VariantSwitcher from '$lib/components/variant-switcher.svelte';

	const reflectionsReady = $derived(reflectionsComplete());

	onMount(() => {
		if (session.active.reflections.length === 0) {
			goto('/', { replaceState: true });
		}
	});

	function exportPdf() {

		const previousTitle = document.title;
		const title = session.active.featureTitle.trim();
		if (title) document.title = title;
		window.print();
		document.title = previousTitle;
	}
</script>

<div class="mx-auto max-w-3xl space-y-6">
	<header class="space-y-2 no-print">
		<h1 class="text-2xl font-semibold">Export & Share</h1>
		<p class="text-sm text-muted-foreground">
			Save your ethical reflections to share with your team or include in documentation.
		</p>
		<VariantSwitcher />
	</header>

	<div class="flex flex-wrap items-center gap-3 no-print">
		<BackButton />
		<Button variant="outline" onclick={exportPdf}>📄 Export as PDF</Button>
		<Button onclick={() => goto('/feedback')} disabled={!reflectionsReady}>Continue to Feedback →</Button>
		{#if !reflectionsReady}
			<span class="text-sm text-muted-foreground">Feedback opens once all reflections have loaded.</span>
		{/if}
	</div>

	<ReportPreview
		featureTitle={session.active.featureTitle}
		description={session.state.description}
		reflections={session.active.reflections}
	/>
</div>
