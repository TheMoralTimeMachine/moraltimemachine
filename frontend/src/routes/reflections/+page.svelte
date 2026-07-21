<script lang="ts">
	import { goto } from '$app/navigation';
	import { DIMENSIONS, DIMENSION_META, type Dimension } from '$lib/api';
	import BackButton from '$lib/components/back-button.svelte';
	import DetailPanel from '$lib/components/detail-panel.svelte';
	import ReflectionCard from '$lib/components/reflection-card.svelte';
	import VariantSwitcher from '$lib/components/variant-switcher.svelte';
	import ViewSwitcher from '$lib/components/view-switcher.svelte';
	import Button from '$lib/components/ui/button.svelte';
	import Card from '$lib/components/ui/card.svelte';
	import { session } from '$lib/stores/session.svelte';
	import { onMount, tick } from 'svelte';

	const TOTAL = DIMENSIONS.length;

	const TOP_ROW = DIMENSIONS.slice(0, 2);
	const BOTTOM_ROW = DIMENSIONS.slice(2);

	const loading = $derived(session.state.loading.reflections);
	const reflections = $derived(session.active.reflections);
	const byDim = (d: Dimension) => reflections.find((r) => r.dimension === d);

	let openDim = $state<Dimension | null>(null);

	async function toggle(dim: Dimension) {
		openDim = openDim === dim ? null : dim;
		if (openDim) {
			await tick();
			scrollPanelTop();
		}
	}

	async function switchTo(dim: Dimension) {
		openDim = dim;
		await tick();
		scrollPanelTop();
	}

	function scrollPanelTop() {
		document.getElementById('risk-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
	}

	onMount(() => {

		if (reflections.length === 0 && !loading && !session.state.error) {
			goto('/', { replaceState: true });
		}

		const onKeydown = (e: KeyboardEvent) => {
			if (e.key === 'Escape' && openDim !== null) openDim = null;
		};
		window.addEventListener('keydown', onKeydown);
		return () => window.removeEventListener('keydown', onKeydown);
	});
</script>

{#snippet gridRow(dims: Dimension[], panelAbove: boolean)}
	<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
		{#each dims as dim (dim)}
			{@const r = byDim(dim)}
			{#if r}
				<ReflectionCard reflection={r} active={openDim === dim} onToggle={() => toggle(dim)} {panelAbove} />
			{:else if loading}
				{@const meta = DIMENSION_META[dim]}
				<Card class="overflow-hidden border-transparent border-trail" aria-hidden="true">
					<div class="space-y-3 p-5">
						<div class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
							{meta.label}
						</div>
						<div class="h-5 w-3/4 animate-pulse rounded bg-muted"></div>
						<div class="space-y-2">
							<div class="h-3 w-full animate-pulse rounded bg-muted"></div>
							<div class="h-3 w-5/6 animate-pulse rounded bg-muted"></div>
						</div>
					</div>
				</Card>
			{/if}
		{/each}
	</div>
{/snippet}

<div class="space-y-6">
	<header class="space-y-2">
		{#if session.active.featureTitle}
			<h1 class="text-2xl font-semibold">{session.active.featureTitle}</h1>
			<p class="text-sm text-muted-foreground">{session.state.description}</p>
		{:else}
			<h1 class="text-2xl font-semibold">Ethical Reflections</h1>
			<p class="text-sm text-muted-foreground">
				Potential consequences across four dimensions, with relevant harm categories tagged.
			</p>
		{/if}
		<VariantSwitcher />
		<ViewSwitcher />
		{#if loading}
			<p class="text-sm text-muted-foreground">
				Generating reflection {Math.min(reflections.length + 1, TOTAL)} of {TOTAL}…
			</p>
		{/if}
	</header>

	{#if session.state.error}
		<Card class="space-y-3 p-6">
			<p class="text-sm text-destructive">{session.state.error}</p>
			<Button variant="outline" onclick={() => goto('/')}>← Start over</Button>
		</Card>
	{/if}

	<div class="flex flex-col gap-4">
		{@render gridRow(TOP_ROW, false)}

		{#if openDim !== null}
			{@const open = byDim(openDim)}
			{#if open}
				<DetailPanel reflection={open} onSwitch={switchTo} onClose={() => (openDim = null)} />
			{/if}
		{/if}

		{@render gridRow(BOTTOM_ROW, true)}
	</div>

	<div class="flex flex-wrap gap-3 pt-2">
		<BackButton />
		<Button onclick={() => goto('/explore')}>Explore Deeper →</Button>
		<Button variant="outline" onclick={() => goto('/export')} disabled={loading}>Skip to Export</Button>
	</div>
</div>
