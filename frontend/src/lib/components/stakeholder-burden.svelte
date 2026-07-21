<script lang="ts">
	import type { HarmRef, Reflection } from '$lib/api';

	let { reflections, includeAffects = false }: { reflections: Reflection[]; includeAffects?: boolean } = $props();

	const HARM_COLOR: Record<string, string> = {
		Disparity: '#a5a0f0',
		Transparency: '#85b7eb',
		Accountability: '#bcb2cf',
		Manipulation: '#c993e6',
		Privacy: '#f09595',
		'False information': '#e6c34a',
		'Inappropriate content': '#ed93b1',
		'Fraudulent activity': '#f0997b',
		'Disruptive activity': '#efaa4a',
		Censorship: '#97c459'
	};
	const harmColor = (cat: string) => HARM_COLOR[cat] ?? '#9a9aa0';

	interface GroupRow {
		name: string;
		total: number;
		segments: { category: string; count: number }[];
	}

	const rows = $derived.by<GroupRow[]>(() => {
		const groups = new Map<string, Map<string, number>>();

		const add = (name: string, harms: HarmRef[]) => {
			const key = name.trim();
			if (!key) return;
			if (!groups.has(key)) groups.set(key, new Map());
			const tally = groups.get(key)!;
			for (const h of harms) tally.set(h.category, (tally.get(h.category) ?? 0) + 1);
		};

		for (const r of reflections) {
			for (const p of r.points) {
				if (p.context_label === 'Stakeholder') {
					add(p.context ?? '', p.harms ?? []);
				} else if (includeAffects && p.context) {

					for (const name of p.context.split(',')) add(name, p.harms ?? []);
				}
			}
		}

		const out: GroupRow[] = [];
		for (const [name, tally] of groups) {
			const segments = [...tally.entries()]
				.map(([category, count]) => ({ category, count }))
				.sort((a, b) => b.count - a.count);
			const total = segments.reduce((s, x) => s + x.count, 0);
			out.push({ name, total, segments });
		}
		return out.sort((a, b) => b.total - a.total);
	});

	const maxTotal = $derived(rows.reduce((m, r) => Math.max(m, r.total), 1));

	const legend = $derived.by(() => {
		const seen = new Set<string>();
		for (const r of rows) for (const s of r.segments) seen.add(s.category);
		return Object.keys(HARM_COLOR).filter((c) => seen.has(c));
	});
</script>

{#if rows.length}
	<div class="burden">
		{#each rows as row (row.name)}
			<div class="row">
				<div class="label">{row.name}</div>
				<div class="track">
					<div class="fill" style={`width:${(row.total / maxTotal) * 100}%`}>
						{#each row.segments as seg (seg.category)}
							<div
								style={`flex:${seg.count}; background:${harmColor(seg.category)}`}
								title={`${seg.category}: ${seg.count}`}
							></div>
						{/each}
					</div>
				</div>
				<div class="num">{row.total}</div>
			</div>
		{/each}

		<div class="legend">
			{#each legend as cat (cat)}
				<span class="item">
					<span class="swatch" style={`background:${harmColor(cat)}`}></span>{cat}
				</span>
			{/each}
		</div>
	</div>
{/if}

<style>
	.burden {
		display: flex;
		flex-direction: column;
		gap: 9px;
		padding: 0.5rem 0;
	}
	.row {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.label {
		width: 200px;
		flex-shrink: 0;
		font-size: 13px;
		line-height: 1.3;
		color: var(--color-foreground);
	}
	.track {
		flex: 1;
		height: 22px;
		border-radius: 5px;
		background: var(--color-muted);
		overflow: hidden;
	}
	.fill {
		display: flex;
		height: 100%;
		border-radius: 5px;
		overflow: hidden;
	}
	.num {
		width: 24px;
		flex-shrink: 0;
		text-align: right;
		font-size: 13px;
		font-weight: 500;
		color: var(--color-foreground);
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 14px;
		margin-top: 8px;
		padding-top: 12px;
		border-top: 0.5px solid var(--color-border);
		font-size: 11px;
		color: var(--color-muted-foreground);
	}
	.legend .item {
		display: flex;
		align-items: center;
		gap: 5px;
	}
	.legend .swatch {
		width: 10px;
		height: 10px;
		border-radius: 2px;
	}
</style>
