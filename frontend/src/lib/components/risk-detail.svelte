<script lang="ts">
	import { type ReflectionPoint } from '$lib/api';
	import { cn } from '$lib/utils';
	import type { LucideIcon } from '@lucide/svelte';
	import Lightbulb from '@lucide/svelte/icons/lightbulb';
	import Megaphone from '@lucide/svelte/icons/megaphone';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import User from '@lucide/svelte/icons/user';
	import Users from '@lucide/svelte/icons/users';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import HarmTag from './harm-tag.svelte';

	const CONTEXT_ICON: Record<string, LucideIcon> = {
		Affects: Users,
		'Raised by': Megaphone,
		Stakeholder: User
	};

	interface Props {
		point: ReflectionPoint;

		variant?: 'report' | 'panel';

		stakeholder?: boolean;

		onExplore?: () => void;
	}

	let { point, variant = 'panel', stakeholder = false, onExplore }: Props = $props();

	const titleView = $derived.by(() => {
		if (stakeholder) return null;
		if (point.title) {
			return { title: point.title, body: point.point };
		}
		const idx = point.point.indexOf(': ');
		if (idx > 0) {
			const left = point.point.slice(0, idx);
			if (left.split(' ').length <= 8) {
				return { title: left, body: point.point.slice(idx + 2) };
			}
		}
		return null;
	});

	const harms = $derived.by(() => {
		const seen = new Set<string>();
		return point.harms.filter((h) => {
			if (seen.has(h.category)) return false;
			seen.add(h.category);
			return true;
		});
	});

	const THEME_VARS =
		'--rd-card-bg:color-mix(in oklch, var(--color-card), var(--color-foreground) 4%);--rd-card-border:var(--color-border);' +
		'--rd-heading:var(--color-foreground);--rd-divider:var(--color-border);' +
		'--rd-label:var(--color-muted-foreground);--rd-value:var(--color-foreground);' +
		'--rd-subtitle:var(--color-muted-foreground);--rd-mit-body:var(--color-muted-foreground);';

	const rootStyle = $derived(
		THEME_VARS +
			(variant === 'report' ? 'margin-bottom:14px;' : '') +
			'background:var(--rd-card-bg);border:0.5px solid var(--rd-card-border);border-radius:12px;padding:16px 18px;'
	);

	const CtxIcon = $derived(point.context_label ? CONTEXT_ICON[point.context_label] : undefined);
</script>

<div class={cn(variant === 'report' && 'pdf-block')} style={rootStyle}>
	{#if stakeholder}
		<div style="display:flex;align-items:center;gap:8px;margin:0 0 8px;">
			<User size={18} color="var(--color-stakeholder-impact)" aria-hidden="true" />
			<p style="font-size:17px;font-weight:500;color:var(--rd-heading);margin:0;">
				{point.context}
			</p>
		</div>
	{:else if titleView}
		<p style="font-size:15px;font-weight:500;color:var(--rd-heading);margin:0 0 6px;">
			{titleView.title}
		</p>
		<p style="font-size:13px;color:var(--rd-subtitle);margin:0 0 8px;line-height:1.55;">
			{titleView.body}
		</p>
	{:else}
		<p style="font-size:15px;font-weight:500;color:var(--rd-heading);margin:0 0 8px;">
			{point.point}
		</p>
	{/if}

	<div style="border-top:0.5px solid var(--rd-divider);padding-top:13px;">
		{#if stakeholder}
			<p style="font-size:13px;color:var(--rd-subtitle);margin:0 0 14px;line-height:1.55;">
				{point.point}
			</p>
		{:else if point.context}
			<div style="display:flex;gap:9px;margin-bottom:14px;align-items:flex-start;">
				<span
					style="font-size:11px;color:var(--rd-label);min-width:64px;padding-top:2px;display:inline-flex;align-items:center;gap:4px;"
				>
					{#if CtxIcon}<CtxIcon size={13} aria-hidden="true" />{/if}
					{point.context_label ?? 'Context'}
				</span>
				<span style="font-size:13px;color:var(--rd-value);line-height:1.5;">
					{point.context}{#if point.context_detail}
						<span style="color:var(--rd-subtitle);font-style:italic;"> · {point.context_detail}</span>
					{/if}
				</span>
			</div>
		{/if}

		{#if harms.length > 0}
			<div style="display:flex;gap:9px;margin-bottom:14px;">
				<span
					style="font-size:11px;color:var(--rd-label);min-width:64px;padding-top:4px;display:inline-flex;align-items:center;gap:3px;"
				>
					<TriangleAlert size={13} aria-hidden="true" />
					Harms
				</span>
				<div style="flex:1;min-width:0;">

					<div
						class={cn(
							variant === 'panel' && 'flex flex-col gap-[9px]',
							variant === 'report' && 'flex flex-wrap gap-2 print:flex-col print:gap-[9px]'
						)}
					>
						{#each harms as harm (harm.category)}
							<div class="flex items-start gap-2">
								<HarmTag {harm} />
								{#if harm.explanation}
									<span
										class={cn('min-w-0 flex-1 pt-[3px]', variant === 'report' && 'hidden print:block')}
										style="font-size:13px;color:var(--rd-mit-body);line-height:1.5;"
									>
										{harm.explanation}
									</span>
								{/if}
							</div>
						{/each}
					</div>
				</div>
			</div>
		{/if}

		{#if point.mitigation}
			<div
				class={cn(variant === 'report' && 'pdf-block')}
				style="background:rgba(99,153,34,0.08);border:0.5px solid rgba(99,153,34,0.28);border-radius:8px;padding:10px 12px;"
			>
				<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
					<Lightbulb size={14} color="#9fcc63" aria-hidden="true" />
					<span style="font-size:12px;font-weight:500;color:#9fcc63;">Mitigation</span>
				</div>
				<p style="font-size:13px;color:var(--rd-mit-body);margin:0;line-height:1.55;">
					{point.mitigation}
				</p>
			</div>
		{/if}

		{#if onExplore && variant === 'panel'}
			<button
				type="button"
				onclick={onExplore}
				class="mt-3 inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
			>
				Explore this risk
				<ArrowRight size={13} aria-hidden="true" />
			</button>
		{/if}
	</div>
</div>
