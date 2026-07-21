<script lang="ts">
	import { goto } from '$app/navigation';
	import { DIMENSIONS, DIMENSION_META, type Dimension, type Reflection, type ReflectionPoint } from '$lib/api';
	import { DIMENSION_ICONS } from '$lib/dimension-icons';
	import { cn } from '$lib/utils';
	import RiskDetail from './risk-detail.svelte';
	import X from '@lucide/svelte/icons/x';

	interface Props {
		reflection: Reflection;
		onSwitch: (dim: Dimension) => void;
		onClose: () => void;
	}

	let { reflection, onSwitch, onClose }: Props = $props();

	const meta = $derived(DIMENSION_META[reflection.dimension]);
	const Icon = $derived(DIMENSION_ICONS[reflection.dimension]);

	const isStakeholder = $derived(reflection.dimension === 'stakeholder_impact');
	const badges = $derived(
		reflection.points
			.map((p, index) => ({ name: isStakeholder ? p.context : p.title, index }))
			.filter((b): b is { name: string; index: number } => !!b.name)
	);

	const badgeIndices = $derived(new Set(badges.map((b) => b.index)));

	let activeIndex = $state<number | null>(null);
	$effect(() => {
		activeIndex = badges[0]?.index ?? null;
	});

	let scrollEl = $state<HTMLElement>();

	let programmaticScroll = false;
	let scrollSettleTimer: ReturnType<typeof setTimeout> | undefined;

	function selectBadge(index: number) {
		activeIndex = index;
		const target = document.getElementById(`risk-point-${index}`);
		if (!scrollEl || !target) return;
		programmaticScroll = true;
		clearTimeout(scrollSettleTimer);

		scrollSettleTimer = setTimeout(() => {
			programmaticScroll = false;
		}, 700);
		const top = target.getBoundingClientRect().top - scrollEl.getBoundingClientRect().top + scrollEl.scrollTop - 8;
		scrollEl.scrollTo({ top, behavior: 'smooth' });
	}

	$effect(() => {

		reflection.dimension;
		const root = scrollEl;
		if (!root) return;

		const visible = new Map<number, boolean>();

		const sync = () => {
			if (programmaticScroll) return;
			let top: number | null = null;
			for (const [index, isVisible] of visible) {
				if (isVisible && badgeIndices.has(index) && (top === null || index < top)) {
					top = index;
				}
			}
			if (top !== null) activeIndex = top;
		};

		const observer = new IntersectionObserver(
			(entries) => {
				for (const entry of entries) {
					const index = Number((entry.target as HTMLElement).dataset.pointIndex);
					visible.set(index, entry.isIntersecting);
				}
				sync();
			},
			{ root, rootMargin: '0px 0px -80% 0px', threshold: 0 }
		);

		for (const el of root.querySelectorAll<HTMLElement>('[data-point-index]')) {
			observer.observe(el);
		}

		const onScrollEnd = () => {
			programmaticScroll = false;
		};
		root.addEventListener('scrollend', onScrollEnd);

		return () => {
			observer.disconnect();
			root.removeEventListener('scrollend', onScrollEnd);
		};
	});

	const SUBTITLE_NOUN: Record<Dimension, string> = {
		tomorrow: 'day-one risk',
		in_five_years: 'long-term risk',
		public_scrutiny: 'scrutiny concern',
		stakeholder_impact: 'affected group'
	};
	const subtitle = $derived.by(() => {
		const n = reflection.points.length;
		return `${n} ${SUBTITLE_NOUN[reflection.dimension]}${n === 1 ? '' : 's'}`;
	});

	const dimIndex = $derived(DIMENSIONS.indexOf(reflection.dimension));
	const isBottomRow = $derived(dimIndex >= 2);
	const isRightCol = $derived(dimIndex % 2 === 1);

	function explorePoint(point: ReflectionPoint) {
		const name = point.title || point.context || point.point;
		const question = `Tell me more about "${name}" (${meta.label}) — why is it a risk and how should I mitigate it?`;
		goto('/explore?q=' + encodeURIComponent(question));
	}

	const arrowStyle = $derived(
		'width:0;height:0;border-left:8px solid transparent;border-right:8px solid transparent;' +
			(isBottomRow
				? `bottom:-8px;border-top:8px solid var(--color-${meta.accent});`
				: `top:-8px;border-bottom:8px solid var(--color-${meta.accent});`)
	);
</script>

<div class="relative">

	<span
		aria-hidden="true"
		class={cn('pointer-events-none absolute left-1/2 -translate-x-1/2', isRightCol ? 'md:left-3/4' : 'md:left-1/4')}
		style={arrowStyle}
	></span>

	<section
		id="risk-panel"
		aria-label="{meta.label} detailed risks"
		class="flex max-h-[70vh] flex-col overflow-hidden rounded-xl border bg-card"
		style="border:2px solid var(--color-{meta.accent});scroll-margin-top:calc(var(--nav-height) + 12px);"
	>

		<div class="flex shrink-0 items-center justify-between gap-3 border-b border-border bg-card px-4 py-3">
			<div class="flex min-w-0 items-center gap-2.5">
				<span
					class="flex h-7 w-7 shrink-0 items-center justify-center rounded-md"
					style="color: var(--color-{meta.accent}); background: color-mix(in oklch, var(--color-{meta.accent}), transparent 84%);"
					aria-hidden="true"
				>
					<Icon size={16} />
				</span>
				<span class="truncate text-sm font-medium">
					<span style="color: var(--color-{meta.accent})">{meta.label}</span>
					<span class="text-muted-foreground">· {subtitle}</span>
				</span>
			</div>

			<div class="flex shrink-0 items-center gap-1">
				{#each DIMENSIONS as dim (dim)}
					{@const dm = DIMENSION_META[dim]}
					{@const DimIcon = DIMENSION_ICONS[dim]}
					{@const isActive = dim === reflection.dimension}
					<button
						type="button"
						onclick={() => onSwitch(dim)}
						aria-label="{dm.label} detailed risks"
						aria-current={isActive ? 'true' : undefined}
						title={dm.label}
						class={cn(
							'flex h-8 w-8 items-center justify-center rounded-md transition-colors',
							!isActive && 'text-muted-foreground hover:bg-accent hover:text-foreground'
						)}
						style={isActive
							? `color: var(--color-${dm.accent}); background: color-mix(in oklch, var(--color-${dm.accent}), transparent 78%);`
							: undefined}
					>
						<DimIcon size={16} />
					</button>
				{/each}

				<span class="mx-1 h-5 w-px bg-border" aria-hidden="true"></span>

				<button
					type="button"
					onclick={onClose}
					aria-label="Close detailed risks"
					title="Close"
					class="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
				>
					<X class="h-4 w-4" />
				</button>
			</div>
		</div>

		{#if badges.length > 0}
			<div class="flex shrink-0 flex-wrap gap-1.5 border-b border-border px-4 py-3">
				{#each badges as badge}
					{@const isActive = badge.index === activeIndex}
					<button
						type="button"
						onclick={() => selectBadge(badge.index)}
						title="Jump to {badge.name}"
						aria-current={isActive ? 'true' : undefined}
						class={cn(
							'inline-flex cursor-pointer items-center rounded-full px-2.5 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-card',
							!isActive && 'text-muted-foreground hover:text-foreground'
						)}
						style={isActive
							? `color: var(--color-${meta.accent}); background: color-mix(in oklch, var(--color-${meta.accent}), transparent 86%); --tw-ring-color: var(--color-${meta.accent});`
							: `background: var(--color-muted); --tw-ring-color: var(--color-${meta.accent});`}
					>
						{badge.name}
					</button>
				{/each}
			</div>
		{/if}

		<div bind:this={scrollEl} class="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-4">
			{#each reflection.points as point, index}
				<div id="risk-point-{index}" data-point-index={index} style="scroll-margin-top:8px;">
					<RiskDetail {point} variant="panel" stakeholder={isStakeholder} onExplore={() => explorePoint(point)} />
				</div>
			{/each}
		</div>
	</section>
</div>
