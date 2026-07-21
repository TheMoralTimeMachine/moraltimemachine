<script lang="ts">
	import { onMount } from 'svelte';
	import { dev } from '$app/environment';
	import { goto } from '$app/navigation';
	import type { GenerationMode, Speed } from '$lib/api';
	import { api, OffTopicError } from '$lib/api';
	import { BACKUP_DESCRIPTION, consumeBackupAutoStart, isBackupTrigger, streamBackupSession } from '$lib/api/backup';
	import { buildReflections } from '$lib/api/mock';
	import Button from '$lib/components/ui/button.svelte';
	import Textarea from '$lib/components/ui/textarea.svelte';
	import { EXAMPLE_PROMPT } from '$lib/examples';
	import { session } from '$lib/stores/session.svelte';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import GitCompare from '@lucide/svelte/icons/git-compare';
	import Hourglass from '@lucide/svelte/icons/hourglass';
	import ListOrdered from '@lucide/svelte/icons/list-ordered';
	import Search from '@lucide/svelte/icons/search';
	import Users from '@lucide/svelte/icons/users';
	import Zap from '@lucide/svelte/icons/zap';

	const horizons = [
		{
			icon: Zap,
			accent: 'tomorrow',
			when: 'Day one',
			title: 'Tomorrow',
			description: 'The harms that surface the moment the feature ships.'
		},
		{
			icon: Hourglass,
			accent: 'in-five-years',
			when: 'Five years',
			title: 'In five years',
			description: 'How those harms compound and spread over years of use.'
		},
		{
			icon: Search,
			accent: 'public-scrutiny',
			when: 'If exposed',
			title: 'Public scrutiny',
			description: 'How regulators, journalists, and the public would react.'
		},
		{
			icon: Users,
			accent: 'stakeholder-impact',
			when: 'Everyone',
			title: 'Stakeholders',
			description: 'Who gets affected, with a focus on groups that are typically overlooked.'
		}
	];

	const speedOptions: {
		value: GenerationMode;
		label: string;
		icon: typeof Zap;
		hint: string;
	}[] = [
		{
			value: 'fast',
			label: 'Fast',
			icon: Zap,
			hint: 'One shared context call, then all four lenses in parallel. Quickest, some overlap.'
		},
		{
			value: 'thinking',
			label: 'Thinking',
			icon: ListOrdered,
			hint: 'All four lenses run one after another, each building on the last. Richest, slowest.'
		},
		{
			value: 'compare',
			label: 'Compare',
			icon: GitCompare,
			hint: 'Run Fast and Thinking together, then switch between them on the next pages to compare.'
		}
	];

	let value = $state(session.state.description ?? '');
	let mode = $state<GenerationMode>(session.state.mode ?? 'fast');
	let error = $state<string | null>(null);

	onMount(() => {
		if (consumeBackupAutoStart()) {
			value = BACKUP_DESCRIPTION;
			generateBackup();
		}
	});

	async function generate() {
		if (isBackupTrigger(value)) {
			await generateBackup();
			return;
		}
		const description = value.trim();
		if (description.length < 10) {
			error = 'Please describe the feature in at least a sentence.';
			return;
		}
		error = null;

		const speeds: Speed[] = mode === 'compare' ? ['fast', 'thinking'] : [mode];
		session.reset();
		session.state.description = description;
		session.state.mode = mode;
		session.state.compare = mode === 'compare';
		session.state.view = speeds[0];
		session.state.loading.reflections = true;
		session.save();

		let navigated = false;
		const enterReflections = () => {
			if (navigated) return;
			navigated = true;
			session.save();
			goto('/reflections');
		};

		const runOne = async (sp: Speed) => {
			const { sessionId, featureTitle } = await api.createSessionStream(
				description,
				sp,
				(reflection) => {
					enterReflections();
					const v = session.state.variants[sp];
					v.reflections = [...v.reflections, reflection];
					session.save();
				},
				(title) => {
					session.state.variants[sp].featureTitle = title;
					enterReflections();
				}
			);
			const v = session.state.variants[sp];
			v.sessionId = sessionId;
			v.featureTitle = featureTitle;
			session.save();
		};

		try {
			const results = await Promise.allSettled(speeds.map(runOne));
			const rejected = results.find((r) => r.status === 'rejected') as PromiseRejectedResult | undefined;
			if (rejected) {
				const reason = rejected.reason;
				if (reason instanceof OffTopicError) {

					error = reason.message;
				} else if (navigated) {

					session.state.error = reason instanceof Error ? reason.message : 'Something went wrong.';
					session.save();
				} else {
					error = reason instanceof Error ? reason.message : 'Something went wrong.';
				}
			}
		} catch (e) {

			error = e instanceof Error ? e.message : 'Something went wrong.';
		} finally {
			session.state.loading.reflections = false;
			session.save();
		}
	}

	async function generateBackup() {
		error = null;
		const description = BACKUP_DESCRIPTION;
		const speeds: Speed[] = mode === 'compare' ? ['fast', 'thinking'] : [mode];
		session.reset();
		session.state.description = description;
		session.state.mode = mode;
		session.state.compare = mode === 'compare';
		session.state.view = speeds[0];
		session.state.loading.reflections = true;
		session.save();

		let navigated = false;
		const enterReflections = () => {
			if (navigated) return;
			navigated = true;
			session.save();
			goto('/reflections');
		};

		const runOne = async (sp: Speed) => {
			const { sessionId, featureTitle } = await streamBackupSession(
				sp,
				(reflection) => {
					enterReflections();
					const v = session.state.variants[sp];
					v.reflections = [...v.reflections, reflection];
					session.save();
				},
				(title) => {
					session.state.variants[sp].featureTitle = title;
					enterReflections();
				}
			);
			const v = session.state.variants[sp];
			v.sessionId = sessionId;
			v.featureTitle = featureTitle;
			session.save();
		};

		try {
			await Promise.allSettled(speeds.map(runOne));
		} finally {
			session.state.loading.reflections = false;
			session.save();
		}
	}

	function skipToReflections() {
		const description = (value.trim() || EXAMPLE_PROMPT).trim();
		session.reset();
		session.state.description = description;
		session.state.view = 'fast';
		session.state.variants.fast = {
			sessionId: 'dev-skip',
			featureTitle: 'AI resume ranking tool',
			reflections: buildReflections(description),
			chat: []
		};
		session.save();
		goto('/reflections');
	}

	const loading = $derived(session.state.loading.reflections);
</script>

<div class="relative">
	<div class="hero-wash pointer-events-none fixed inset-0 -z-10" aria-hidden="true"></div>

	<div class="relative mx-auto max-w-3xl space-y-12 py-6 text-center">

		<div class="space-y-6">
			<h1
				class="reveal mx-auto max-w-2xl font-display text-5xl font-semibold leading-[1.05] tracking-tight sm:text-6xl"
				style="animation-delay:60ms"
			>
				See the ethical consequences of your
				<span class="whitespace-nowrap">feature before you build it.</span>
			</h1>

			<p class="reveal mx-auto max-w-xl text-base leading-relaxed text-muted-foreground" style="animation-delay:120ms">
				Describe a software feature and the Moral Time Machine surfaces how it could cause harm through four lenses,
				each grounded in documented real-world cases and paired with concrete mitigations.
			</p>
		</div>

		<div class="reveal grid grid-cols-1 gap-4 text-left sm:grid-cols-2" style="animation-delay:180ms">
			{#each horizons as horizon, i (horizon.title)}
				{@const Icon = horizon.icon}
				<div class="reveal flex items-start gap-3" style={`animation-delay:${220 + i * 70}ms`}>
					<div
						class="flex size-10 shrink-0 items-center justify-center rounded-xl"
						style={`color:var(--color-${horizon.accent});background:color-mix(in oklch, var(--color-${horizon.accent}), transparent 85%);`}
					>
						<Icon size={19} />
					</div>
					<div class="space-y-0.5">
						<div class="font-semibold leading-tight">{horizon.title}</div>
						<p class="text-sm leading-snug text-muted-foreground">
							{horizon.description}
						</p>
					</div>
				</div>
			{/each}
		</div>

		<div
			class={`reveal mx-auto max-w-2xl rounded-2xl border border-border bg-card p-6 text-left shadow-sm sm:p-7 ${loading ? 'border-transparent border-trail' : ''}`}
			style="animation-delay:520ms"
		>
			<div class="flex flex-wrap items-center justify-between gap-3">
				<div class="space-y-1">
					<h2 class="text-lg font-semibold">What are you building?</h2>
					<p class="text-sm text-muted-foreground">Describe the software feature or system you are implementing.</p>
				</div>
			</div>

			<Textarea
				bind:value
				class="bg-textarea mt-4 border-foreground/15"
				rows={5}
				placeholder="An AI tool that automatically ranks job applicants based on their resume, work history, and online presence..."
				disabled={loading}
			/>

			<div class="mt-4 flex flex-wrap items-center gap-2">
				<span class="text-xs font-medium text-muted-foreground">Speed</span>
				<div
					class="inline-flex rounded-full border border-border bg-muted/40 p-0.5"
					role="radiogroup"
					aria-label="Generation speed"
				>
					{#each speedOptions.filter((o) => dev || (o.value !== 'compare' && o.value !== 'thinking')) as opt (opt.value)}
						{@const Icon = opt.icon}
						{@const active = mode === opt.value}
						<button
							type="button"
							role="radio"
							aria-checked={active}
							title={opt.hint}
							disabled={loading}
							onclick={() => (mode = opt.value)}
							class={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors disabled:opacity-50 ${
								active ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
							}`}
						>
							<Icon size={13} />
							<span>{opt.label}</span>
						</button>
					{/each}
				</div>
			</div>

			{#if error}
				<p class="mt-3 text-sm text-destructive">{error}</p>
			{/if}

			<div class="mt-4 flex items-center justify-between gap-3">
				<Button onclick={generate} disabled={loading} class="gap-2">
					{#if loading}
						Generating…
					{:else}
						Generate reflections
						<ArrowRight size={16} />
					{/if}
				</Button>

				{#if dev}
					<button
						type="button"
						class="inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border border-dashed border-border px-[11px] py-[5px] text-xs font-medium text-muted-foreground transition hover:text-foreground disabled:opacity-50"
						onclick={skipToReflections}
						disabled={loading}
					>
						<Zap size={14} />
						<span>Skip → reflections (dev)</span>
					</button>
				{/if}
			</div>
		</div>
	</div>
</div>
