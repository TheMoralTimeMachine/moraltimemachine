<script lang="ts">
	import { DIMENSIONS, DIMENSION_META, type Dimension, type HarmCategory, type Reflection } from '$lib/api';
	import { DIMENSION_ICONS } from '$lib/dimension-icons';

	let { reflections }: { reflections: Reflection[] } = $props();

	const HARM_ORDER: HarmCategory[] = [
		'Disparity',
		'Transparency',
		'Accountability',
		'Manipulation',
		'False information',
		'Privacy',
		'Inappropriate content',
		'Fraudulent activity',
		'Disruptive activity',
		'Censorship'
	];

	const counts = $derived.by(() => {
		const map: Record<string, Record<Dimension, number>> = {};
		for (const cat of HARM_ORDER) {
			map[cat] = Object.fromEntries(DIMENSIONS.map((d) => [d, 0])) as Record<Dimension, number>;
		}
		for (const r of reflections) {
			for (const p of r.points) {
				for (const h of p.harms ?? []) {
					if (map[h.category]) map[h.category][r.dimension] += 1;
				}
			}
		}
		return map;
	});

	const rowTotal = (cat: string) => DIMENSIONS.reduce((s, d) => s + counts[cat][d], 0);
	const colTotal = (d: Dimension) => rows.reduce((s, cat) => s + counts[cat][d], 0);

	const rows = $derived(
		HARM_ORDER.filter((cat) => DIMENSIONS.some((d) => counts[cat][d] > 0)).sort((a, b) => rowTotal(b) - rowTotal(a))
	);

	const RAMP = ['#e9eff7', '#ccdcec', '#a7c1df', '#8aa0d0', '#8174bb', '#934f9f', '#af2c8d'];
	const cellBg = (n: number) => RAMP[Math.min(n, RAMP.length - 1)];

	const cellFg = (n: number) => (n >= 4 ? '#f3e9f4' : '#243a5e');
</script>

<div class="matrix" style={`--cols:${DIMENSIONS.length}`}>
	<div></div>
	{#each DIMENSIONS as dim (dim)}
		{@const meta = DIMENSION_META[dim]}
		{@const Icon = DIMENSION_ICONS[dim]}
		<div class="head">
			<span style={`color:var(--color-${meta.accent})`}><Icon size={14} aria-hidden="true" /></span>
			<span>{meta.label}</span>
		</div>
	{/each}
	<div class="head sigma">Total</div>

	{#each rows as cat (cat)}
		<div class="rowlabel">{cat}</div>
		{#each DIMENSIONS as dim (dim)}
			{@const n = counts[cat][dim]}
			<div class="cell" style={`background:${cellBg(n)}; color:${cellFg(n)}`}>
				{#if n > 0}{n}{/if}
			</div>
		{/each}
		<div class="total">{rowTotal(cat)}</div>
	{/each}

	<div class="rowlabel foot">Total per lens</div>
	{#each DIMENSIONS as dim (dim)}
		<div class="total foot">{colTotal(dim)}</div>
	{/each}
	<div class="foot"></div>
</div>

<div class="legend">
	<span>fewer</span>
	{#each RAMP as c (c)}
		<span class="swatch" style={`background:${c}`}></span>
	{/each}
	<span>more mentions</span>
</div>

<style>
	.matrix {
		display: grid;
		grid-template-columns: 124px repeat(var(--cols), minmax(0, 1fr)) 44px;
		gap: 4px;
		align-items: center;
	}
	.head {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2px;
		font-size: 12px;
		color: var(--color-muted-foreground);
		padding-bottom: 6px;
		text-align: center;
	}
	.head.sigma {
		font-size: 11px;
		color: var(--color-muted-foreground);
	}
	.rowlabel {
		font-size: 13px;
		color: var(--color-foreground);
	}
	.cell {
		height: 36px;
		border-radius: 6px;
		border: 0.5px solid var(--color-border);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 13px;
	}
	.total {
		text-align: center;
		font-size: 13px;
		font-weight: 500;
		color: var(--color-foreground);
	}
	.foot {
		margin-top: 8px;
		padding-top: 8px;
		border-top: 0.5px solid var(--color-border);
	}
	.rowlabel.foot {
		font-size: 12px;
		color: var(--color-muted-foreground);
	}
	.legend {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-top: 16px;
		font-size: 11px;
		color: var(--color-muted-foreground);
	}
	.legend .swatch {
		width: 22px;
		height: 12px;
		border-radius: 3px;
	}
</style>
