<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { api, DuplicateFeedbackError, type FeedbackRequest } from '$lib/api';
	import { session } from '$lib/stores/session.svelte';
	import { reflectionsComplete } from '$lib/stages';
	import {
		DEMOGRAPHIC_QUESTIONS,
		LIKERT_QUESTIONS,
		LIKERT_SCALE,
		OPEN_QUESTIONS,
		type DemographicQuestion
	} from '$lib/questionnaire';
	import Card from '$lib/components/ui/card.svelte';
	import Button from '$lib/components/ui/button.svelte';
	import Textarea from '$lib/components/ui/textarea.svelte';
	import Input from '$lib/components/ui/input.svelte';
	import BackButton from '$lib/components/back-button.svelte';

	let likert = $state<Record<string, number | null>>({ ...session.state.feedbackAnswers.likert });

	let open = $state<Record<string, string>>({
		...Object.fromEntries(OPEN_QUESTIONS.map((q) => [q.id, ''])),
		...session.state.feedbackAnswers.open
	});

	const OTHER = '__other__';
	let demoChoice = $state<Record<string, string>>({
		...session.state.feedbackAnswers.demographics.choice
	});
	let demoOther = $state<Record<string, string>>({
		...Object.fromEntries(DEMOGRAPHIC_QUESTIONS.filter((q) => q.other).map((q) => [q.id, ''])),
		...session.state.feedbackAnswers.demographics.other
	});
	let submitting = $state(false);
	let error = $state<string | null>(null);

	function demoValue(q: DemographicQuestion): string {
		const choice = demoChoice[q.id];
		if (choice === OTHER) return (demoOther[q.id] ?? '').trim();
		return choice ?? '';
	}

	$effect(() => {
		const snapshot = {
			likert: { ...likert },
			open: { ...open },
			demographics: { choice: { ...demoChoice }, other: { ...demoOther } }
		};
		untrack(() => {
			session.state.feedbackAnswers = snapshot;
			session.save();
		});
	});

	const complete = $derived(
		LIKERT_QUESTIONS.every((q) => likert[q.id] !== undefined) &&
			OPEN_QUESTIONS.every((q) => q.optional || (open[q.id] ?? '').trim() !== '') &&
			DEMOGRAPHIC_QUESTIONS.every((q) => q.optional || demoValue(q) !== '')
	);

	onMount(() => {

		if (!reflectionsComplete()) {
			goto(session.active.reflections.length > 0 ? '/reflections' : '/', { replaceState: true });
		}
	});

	async function submit() {
		if (!complete || submitting) return;
		submitting = true;
		error = null;

		const payload: FeedbackRequest = {
			sessionIds: {
				fast: session.state.variants.fast.sessionId ?? undefined,
				thinking: session.state.variants.thinking.sessionId ?? undefined
			},
			mode: session.state.mode,
			likert: { ...likert },
			open: Object.fromEntries(OPEN_QUESTIONS.map((q) => [q.id, (open[q.id] ?? '').trim()])),
			demographics: Object.fromEntries(DEMOGRAPHIC_QUESTIONS.map((q) => [q.id, demoValue(q)])),
			questions: Object.fromEntries([
				...LIKERT_QUESTIONS.map((q) => [q.id, q.text]),
				...OPEN_QUESTIONS.map((q) => [q.id, q.label]),
				...DEMOGRAPHIC_QUESTIONS.map((q) => [q.id, q.question])
			])
		};

		try {
			await api.submitFeedback(payload);
			session.state.feedbackSubmitted = true;
			session.save();
		} catch (e) {
			if (e instanceof DuplicateFeedbackError) {

				session.state.feedbackSubmitted = true;
				session.save();
			} else {
				error = 'Submitting failed. Please try again — your answers are still here.';
			}
		} finally {
			submitting = false;
		}
	}

	function startOver() {
		session.reset();
		goto('/', { replaceState: true });
	}
</script>

<div class="mx-auto max-w-3xl space-y-6">
	{#if session.state.feedbackSubmitted}
		<Card class="space-y-4 p-10 text-center">
			<div class="text-4xl">🙏</div>
			<h1 class="text-2xl font-semibold">Thank you!</h1>
			<p class="text-sm text-muted-foreground">
				Your feedback has been recorded. This completes the study session — you can close this tab, or start over to
				explore another feature.
			</p>
			<div class="flex justify-center pt-2">
				<Button variant="outline" onclick={startOver}>↩ Start Over</Button>
			</div>
		</Card>
	{:else}
		<header class="space-y-2">
			<h1 class="text-2xl font-semibold">Feedback</h1>
			<p class="text-sm text-muted-foreground">
				You're done exploring — last step of the study. Rate how well the reflections worked for the feature you
				described, and tell us more in the open questions — your answers there are especially valuable to us.
			</p>
		</header>

		<Card class="space-y-6 p-6">
			<p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">
				1 = Strongly disagree · 5 = Strongly agree
			</p>
			{#each LIKERT_QUESTIONS as q, i (q.id)}
				<fieldset class="space-y-2 {i > 0 ? 'border-t border-border pt-5' : ''}">
					<legend class="pb-1 text-sm font-medium">{i + 1}. {q.text}</legend>
					<div class="flex flex-wrap gap-2" role="radiogroup" aria-label={q.text}>
						{#each LIKERT_SCALE as option (option.value)}
							<label
								class="flex h-9 w-12 cursor-pointer items-center justify-center rounded-md border text-sm transition-colors
                  {likert[q.id] === option.value
									? 'border-primary bg-primary text-primary-foreground'
									: 'border-input bg-background hover:bg-accent'}"
								title={option.label}
							>
								<input
									type="radio"
									class="sr-only"
									name={q.id}
									value={option.value}
									checked={likert[q.id] === option.value}
									onchange={() => (likert[q.id] = option.value)}
								/>
								{option.value}
							</label>
						{/each}
						{#if q.allowNa}
							<label
								class="ml-2 flex h-9 cursor-pointer items-center justify-center rounded-md border px-3 text-sm transition-colors
                  {likert[q.id] === null
									? 'border-primary bg-primary text-primary-foreground'
									: 'border-input bg-background text-muted-foreground hover:bg-accent'}"
								title="Select this if you didn't open the Explore Deeper chat"
							>
								<input
									type="radio"
									class="sr-only"
									name={q.id}
									checked={likert[q.id] === null}
									onchange={() => (likert[q.id] = null)}
								/>
								Did not use
							</label>
						{/if}
					</div>
				</fieldset>
			{/each}
		</Card>

		<Card class="space-y-5 p-6">
			{#each OPEN_QUESTIONS as q (q.id)}
				<div class="space-y-2">
					<label class="text-sm font-medium" for={q.id}>{q.label}</label>
					<Textarea id={q.id} bind:value={open[q.id]} rows={3} />
				</div>
			{/each}
		</Card>

		<Card class="space-y-6 p-6">
			<div class="space-y-1">
				<h2 class="text-base font-semibold">About you</h2>
				<p class="text-sm text-muted-foreground">
					A few short questions about your background, so we can describe who took part in the study.
				</p>
			</div>
			{#each DEMOGRAPHIC_QUESTIONS as q, i (q.id)}
				<fieldset class="space-y-2 border-t border-border pt-5">
					<legend class="pb-1 text-sm font-medium">
						{i + 1}. {q.question}
						{#if q.optional}
							<span class="font-normal text-muted-foreground">(optional)</span>
						{/if}
					</legend>
					<div class="flex flex-col gap-2" role="radiogroup" aria-label={q.question}>
						{#each q.options as option (option)}
							<label
								class="flex cursor-pointer items-center gap-2.5 rounded-md border px-3 py-2 text-sm transition-colors
                  {demoChoice[q.id] === option
									? 'border-primary bg-primary/5'
									: 'border-input bg-background hover:bg-accent'}"
							>
								<input
									type="radio"
									class="h-4 w-4 accent-primary"
									name={q.id}
									value={option}
									checked={demoChoice[q.id] === option}
									onchange={() => (demoChoice[q.id] = option)}
								/>
								{option}
							</label>
						{/each}
						{#if q.other}
							<label
								class="flex cursor-pointer items-center gap-2.5 rounded-md border px-3 py-2 text-sm transition-colors
                  {demoChoice[q.id] === OTHER
									? 'border-primary bg-primary/5'
									: 'border-input bg-background hover:bg-accent'}"
							>
								<input
									type="radio"
									class="h-4 w-4 accent-primary"
									name={q.id}
									checked={demoChoice[q.id] === OTHER}
									onchange={() => (demoChoice[q.id] = OTHER)}
								/>
								{q.other.label}
							</label>
							{#if demoChoice[q.id] === OTHER}
								<Input
									class="ml-7 max-w-sm"
									placeholder={q.other.placeholder}
									aria-label={q.other.label}
									bind:value={demoOther[q.id]}
								/>
							{/if}
						{/if}
					</div>
				</fieldset>
			{/each}
		</Card>

		<div class="flex flex-wrap items-center gap-3 pb-8">
			<BackButton />
			<Button onclick={submit} disabled={!complete || submitting}>
				{submitting ? 'Submitting…' : 'Submit feedback'}
			</Button>
			{#if !complete}
				<span class="text-sm text-muted-foreground">Please answer all questions.</span>
			{:else if error}
				<span class="text-sm text-destructive" role="alert">{error}</span>
			{/if}
		</div>
	{/if}
</div>
