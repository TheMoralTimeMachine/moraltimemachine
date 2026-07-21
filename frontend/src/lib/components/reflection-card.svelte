<script lang="ts">
	import { DIMENSION_META, type Dimension, type Reflection } from '$lib/api';
	import { DIMENSION_ICONS } from '$lib/dimension-icons';
	import Card from './ui/card.svelte';
	import HarmTag from './harm-tag.svelte';
	import Lightbulb from '@lucide/svelte/icons/lightbulb';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';

	interface Props {
		reflection: Reflection;
		active?: boolean;
		onToggle?: () => void;

		panelAbove?: boolean;
	}

	let { reflection, active = false, onToggle, panelAbove = false }: Props = $props();

	const RISK_NOUN: Record<Dimension, string> = {
		tomorrow: 'day-one risks',
		in_five_years: 'long-term risks',
		public_scrutiny: 'scrutiny concerns',
		stakeholder_impact: 'affected stakeholders'
	};

	const meta = $derived(DIMENSION_META[reflection.dimension]);
	const Icon = $derived(DIMENSION_ICONS[reflection.dimension]);
	const noun = $derived(RISK_NOUN[reflection.dimension]);

	const expandable = $derived(reflection.points.length > 0);

	function onContentKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onToggle?.();
		}
	}
</script>

<Card
	class="flex h-full flex-col overflow-hidden"
	style={active
		? `border-color: var(--color-${meta.accent}); box-shadow: 0 0 0 2px var(--color-${meta.accent})`
		: undefined}
>

	<div
		class="space-y-3 p-5 {expandable ? 'cursor-pointer' : ''}"
		onclick={expandable ? onToggle : undefined}
		onkeydown={expandable ? onContentKeydown : undefined}
		role={expandable ? 'button' : undefined}
		tabindex={expandable ? 0 : undefined}
		aria-expanded={expandable ? active : undefined}
		aria-controls={expandable ? 'risk-panel' : undefined}
	>
		<div
			class="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide"
			style="color: var(--color-{meta.accent})"
		>
			<Icon size={13} aria-hidden="true" />
			{meta.label}
		</div>
		<h3 class="text-lg font-semibold leading-tight">{reflection.title}</h3>
		<p class="text-sm text-muted-foreground">{reflection.body}</p>
		{#if reflection.harms.length > 0}
			<div class="flex flex-wrap gap-1.5 pt-1">
				{#each reflection.harms as harm}
					<HarmTag {harm} />
				{/each}
			</div>
		{/if}
		{#if reflection.mitigation}
			<div
				style="background:rgba(99,153,34,0.08);border:0.5px solid rgba(99,153,34,0.28);border-radius:8px;padding:10px 12px;"
			>
				<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
					<Lightbulb size={14} color="#9fcc63" aria-hidden="true" />
					<span style="font-size:12px;font-weight:500;color:#9fcc63;">Recommended mitigation</span>
				</div>
				<p style="font-size:13px;color:#a8a8ad;margin:0;line-height:1.55;">{reflection.mitigation}</p>
			</div>
		{/if}
	</div>

	{#if reflection.points.length > 0}
		<button
			type="button"
			onclick={onToggle}
			aria-expanded={active}
			aria-controls="risk-panel"
			style={active ? `color: var(--color-${meta.accent})` : undefined}
			class="mt-auto flex w-full items-center justify-between border-t border-border px-5 py-3 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
		>
			<span>{active ? `Hide ${noun}` : `View ${reflection.points.length} ${noun}`}</span>
			<ChevronDown class="h-4 w-4 transition-transform {active !== panelAbove ? 'rotate-180' : ''}" />
		</button>
	{/if}
</Card>
