<script lang="ts">
	import { DIMENSION_META, type Reflection } from '$lib/api';
	import { DIMENSION_ICONS } from '$lib/dimension-icons';
	import HarmLensMatrix from './harm-lens-matrix.svelte';
	import HarmTag from './harm-tag.svelte';
	import RiskDetail from './risk-detail.svelte';
	import StakeholderBurden from './stakeholder-burden.svelte';
	import Clock from '@lucide/svelte/icons/clock';
	import Lightbulb from '@lucide/svelte/icons/lightbulb';

	interface Props {
		featureTitle?: string;
		description: string;
		reflections: Reflection[];
	}

	let { featureTitle, description, reflections }: Props = $props();

	const theme = {
		page: 'var(--color-card)',
		pageBorder: 'var(--color-border)',
		cardBg: 'color-mix(in oklch, var(--color-card), var(--color-foreground) 4%)',
		cardBorder: 'var(--color-border)',
		summaryBg: 'color-mix(in oklch, var(--color-card), var(--color-foreground) 4%)',
		summaryBorder: 'var(--color-border)',
		featureBg: 'color-mix(in oklch, var(--color-card), var(--color-foreground) 2.5%)',
		title: 'var(--color-foreground)',
		heading: 'var(--color-foreground)',
		body: 'var(--color-muted-foreground)',
		bodyStrong: 'var(--color-muted-foreground)',
		label: 'var(--color-muted-foreground)',
		subtitle: 'var(--color-muted-foreground)',
		feature: 'var(--color-foreground)',
		divider: 'var(--color-border)',
		chipNeutralBg: 'var(--color-muted)',
		chipNeutralText: 'var(--color-muted-foreground)',
		mitigationText: '#9fcc63',
		mitigationBg: 'rgba(99,153,34,0.08)',
		mitigationBorder: 'rgba(99,153,34,0.28)'
	};
</script>

{#snippet harmList(harms: Reflection['harms'])}

	<div class="flex flex-wrap gap-2 print:flex-col print:gap-[9px]">
		{#each harms as harm}
			<div class="flex items-start gap-2">
				<HarmTag {harm} />
				{#if harm.explanation}
					<span
						class="hidden min-w-0 flex-1 pt-[3px] print:block"
						style="font-size:13px;color:{theme.bodyStrong};line-height:1.5;"
					>
						{harm.explanation}
					</span>
				{/if}
			</div>
		{/each}
	</div>
{/snippet}

{#snippet mitigationCallout(label: string, text: string)}
	<div
		class="pdf-block"
		style="background:{theme.mitigationBg};border:0.5px solid {theme.mitigationBorder};border-radius:8px;padding:10px 12px;"
	>
		<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
			<Lightbulb size={14} color={theme.mitigationText} aria-hidden="true" />
			<span style="font-size:12px;font-weight:500;color:{theme.mitigationText};">{label}</span>
		</div>
		<p style="font-size:13px;color:{theme.bodyStrong};margin:0;line-height:1.55;">{text}</p>
	</div>
{/snippet}

{#snippet horizonSection(reflection: Reflection)}
	{@const meta = DIMENSION_META[reflection.dimension]}
	{@const Icon = DIMENSION_ICONS[reflection.dimension]}
	<section>
		<div class="pdf-keep-next" style="display:flex;align-items:center;gap:8px;margin-bottom:16px;">
			<Icon size={15} color="var(--color-{meta.accent})" aria-hidden="true" />
			<span
				style="font-size:13px;font-weight:600;letter-spacing:0.04em;text-transform:uppercase;color:var(--color-{meta.accent});"
				>{meta.label}</span
			>
			<span style="flex:1;height:0.5px;background:{theme.pageBorder};"></span>
		</div>

		<div
			class="pdf-block"
			style="background:{theme.summaryBg};border:0.5px solid {theme.summaryBorder};border-radius:12px;padding:18px 20px;margin-bottom:22px;"
		>
			<span
				style="display:inline-block;font-size:11px;letter-spacing:0.6px;color:{theme.bodyStrong};background:{theme.chipNeutralBg};padding:3px 9px;border-radius:6px;margin-bottom:12px;"
			>
				Summary
			</span>
			<p style="font-size:16px;font-weight:500;color:{theme.title};margin:0 0 9px;">{reflection.title}</p>
			<p style="font-size:14px;color:{theme.bodyStrong};margin:0 0 14px;line-height:1.65;">{reflection.body}</p>
			{#if reflection.harms.length > 0}
				<div style="margin-bottom:16px;">
					{@render harmList(reflection.harms)}
				</div>
			{/if}
			{#if reflection.mitigation}
				{@render mitigationCallout('Recommended mitigation', reflection.mitigation)}
			{/if}
		</div>

		{#if reflection.points.length > 0}
			<p style="font-size:11px;letter-spacing:1px;color:{theme.label};margin:0 0 12px;">Detailed risks</p>
			{#each reflection.points as point}
				<RiskDetail {point} variant="report" stakeholder={reflection.dimension === 'stakeholder_impact'} />
			{/each}
		{/if}
	</section>
{/snippet}

<div
	style="background:{theme.page};border:1px solid {theme.pageBorder};border-radius:16px;padding:26px 26px 28px;max-width:720px;margin-inline:auto;"
>
	<header style="margin-bottom:22px;">
		<p style="font-size:22px;font-weight:500;color:{theme.title};margin:0 0 3px;">
			{featureTitle ?? 'Moral Time Machine Report'}
		</p>
		<p style="font-size:13px;color:{theme.subtitle};margin:0;display:flex;align-items:center;gap:6px;">
			<Clock size={14} aria-hidden="true" />Moral Time Machine report
		</p>
	</header>

	<div
		class="pdf-block"
		style="background:{theme.featureBg};border:0.5px solid {theme.pageBorder};border-radius:12px;padding:14px 16px;margin-bottom:28px;"
	>
		<p style="font-size:11px;letter-spacing:1px;color:{theme.label};margin:0 0 6px;">Feature description</p>
		<p style="font-size:14px;color:{theme.feature};margin:0;line-height:1.6;">{description}</p>
	</div>

	<section style="margin-bottom:28px;">
		<div class="pdf-keep-next" style="display:flex;align-items:center;gap:8px;margin-bottom:16px;">
			<span style="font-size:13px;font-weight:600;letter-spacing:0.04em;text-transform:uppercase;color:{theme.heading};"
				>Analysis overview</span
			>
			<span style="flex:1;height:0.5px;background:{theme.pageBorder};"></span>
		</div>

		<div
			class="pdf-block"
			style="background:{theme.cardBg};border:0.5px solid {theme.cardBorder};border-radius:12px;padding:18px 20px;margin-bottom:14px;"
		>
			<p style="font-size:11px;letter-spacing:1px;color:{theme.label};margin:0 0 4px;">Harm frequency by lens</p>
			<p style="font-size:13px;color:{theme.body};margin:0 0 14px;line-height:1.5;">
				How often each harm category is mentioned per lens — frequency, not severity.
			</p>
			<HarmLensMatrix {reflections} />
		</div>

		<div
			class="pdf-block"
			style="background:{theme.cardBg};border:0.5px solid {theme.cardBorder};border-radius:12px;padding:18px 20px;"
		>
			<p style="font-size:11px;letter-spacing:1px;color:{theme.label};margin:0 0 4px;">Stakeholder burden</p>
			<p style="font-size:13px;color:{theme.body};margin:0 0 6px;line-height:1.5;">
				Affected groups ranked by how many harm tags touch them, segmented by category.
			</p>
			<StakeholderBurden {reflections} />
		</div>
	</section>

	{#each reflections as reflection}
		<div style="margin-bottom:28px;">
			{@render horizonSection(reflection)}
		</div>
	{/each}
</div>
