<script lang="ts">
	import { goto } from '$app/navigation';
	import HarmLensMatrix from '$lib/components/harm-lens-matrix.svelte';
	import StakeholderBurden from '$lib/components/stakeholder-burden.svelte';
	import VariantSwitcher from '$lib/components/variant-switcher.svelte';
	import ViewSwitcher from '$lib/components/view-switcher.svelte';
	import Button from '$lib/components/ui/button.svelte';
	import Card from '$lib/components/ui/card.svelte';
	import { session } from '$lib/stores/session.svelte';
	import { onMount } from 'svelte';

	const loading = $derived(session.state.loading.reflections);
	const reflections = $derived(session.active.reflections);

	const riskCount = $derived(reflections.reduce((n, r) => n + r.points.length, 0));
	const mitigationCount = $derived.by(() => {
		const set = new Set<string>();
		for (const r of reflections) {
			if (r.mitigation?.trim()) set.add(r.mitigation.trim().toLowerCase());
			for (const p of r.points) if (p.mitigation?.trim()) set.add(p.mitigation.trim().toLowerCase());
		}
		return set.size;
	});

	const topHarm = $derived.by(() => {
		const tally = new Map<string, number>();
		for (const r of reflections)
			for (const p of r.points) for (const h of p.harms ?? []) tally.set(h.category, (tally.get(h.category) ?? 0) + 1);
		let top: { category: string; count: number } | null = null;
		for (const [category, count] of tally) if (!top || count > top.count) top = { category, count };
		return top;
	});

	const topGroup = $derived.by(() => {
		const tally = new Map<string, number>();
		for (const r of reflections) {
			for (const p of r.points) {
				if (p.context_label !== 'Stakeholder') continue;
				const name = p.context?.trim();
				if (!name) continue;
				tally.set(name, (tally.get(name) ?? 0) + (p.harms?.length ?? 0));
			}
		}
		let top: { name: string; count: number } | null = null;
		for (const [name, count] of tally) if (!top || count > top.count) top = { name, count };
		return top;
	});

	onMount(() => {

		if (reflections.length === 0 && !loading && !session.state.error) {
			goto('/', { replaceState: true });
		}
	});
</script>

{#snippet stat(label: string, value: string, detail: string | null)}
	<Card class="space-y-1 p-4">
		<p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">
			{label}
		</p>
		<p class="truncate text-lg font-semibold" title={value}>{value}</p>
		{#if detail}
			<p class="text-xs text-muted-foreground">{detail}</p>
		{/if}
	</Card>
{/snippet}

<div class="space-y-6">
	<header class="space-y-2">
		{#if session.active.featureTitle}
			<h1 class="text-2xl font-semibold">{session.active.featureTitle}</h1>
			<p class="text-sm text-muted-foreground">{session.state.description}</p>
		{:else}
			<h1 class="text-2xl font-semibold">Insights</h1>
			<p class="text-sm text-muted-foreground">Aggregate view of this session's ethical reflections.</p>
		{/if}
		<VariantSwitcher />
		<ViewSwitcher />
		{#if loading}
			<p class="text-sm text-muted-foreground">Still generating — these aggregates update as reflections arrive.</p>
		{/if}
	</header>

	<div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
		{@render stat('Risks identified', String(riskCount), 'detail points across 4 lenses')}
		{@render stat('Distinct mitigations', String(mitigationCount), 'deduplicated recommendations')}
		{@render stat('Most-mentioned harm', topHarm?.category ?? '—', topHarm ? `${topHarm.count} mentions` : null)}
		{@render stat(
			'Most-affected group',
			topGroup?.name ?? '—',
			topGroup ? `touched by ${topGroup.count} harm tags` : null
		)}
	</div>

	<Card class="space-y-3 p-6">
		<div>
			<h2 class="text-base font-semibold">Harm frequency by lens</h2>
			<p class="text-sm text-muted-foreground">
				How often each harm category is mentioned per lens — where the analysis concentrates. Frequency, not severity.
			</p>
		</div>
		<HarmLensMatrix {reflections} />
	</Card>

	<Card class="space-y-3 p-6">
		<div>
			<h2 class="text-base font-semibold">Stakeholder burden</h2>
			<p class="text-sm text-muted-foreground">
				Affected groups ranked by how many harm tags touch them, segmented by harm category.
			</p>
		</div>
		<StakeholderBurden {reflections} />
	</Card>

	<div class="flex flex-wrap gap-3 pt-2">
		<Button variant="outline" onclick={() => goto('/reflections')}>← Back</Button>
		<Button onclick={() => goto('/explore')}>Explore Deeper →</Button>
		<Button variant="outline" onclick={() => goto('/export')} disabled={loading}>Skip to Export</Button>
	</div>
</div>
