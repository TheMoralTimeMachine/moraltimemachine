<script lang="ts">
	import type { AdminFeedbackEntry, AdminParticipant, AdminSession } from '$lib/api/admin';
	import {
		DEMOGRAPHIC_QUESTIONS,
		LIKERT_QUESTIONS,
		LIKERT_SCALE,
		OPEN_QUESTIONS
	} from '$lib/questionnaire';
	import Badge from '$lib/components/ui/badge.svelte';
	import Button from '$lib/components/ui/button.svelte';

	interface Props {
		participant: AdminParticipant;
		entries: AdminFeedbackEntry[];
		sessions: AdminSession[];
		loading: boolean;
		error: string | null;
		onClose: () => void;
	}

	let { participant, entries, sessions, loading, error, onClose }: Props = $props();

	function questionText(entry: AdminFeedbackEntry, id: string, fallback: string): string {
		return entry.questions[id]?.trim() || fallback;
	}

	function scaleLabel(value: number | null): string {
		if (value === null) return 'Did not use';
		return LIKERT_SCALE.find((s) => s.value === value)?.label ?? `${value}`;
	}

	const fmt = (ts: string | null) => (ts ? ts.slice(0, 16) : '—');

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') onClose();
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div
	class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4 sm:p-8"
	role="dialog"
	aria-modal="true"
	aria-label="Participant answers"
>

	<button
		type="button"
		class="absolute inset-0 cursor-default"
		aria-label="Close"
		onclick={onClose}
	></button>

	<div
		class="relative z-10 w-full max-w-2xl rounded-xl border border-border bg-card text-card-foreground shadow-xl"
	>
		<header
			class="flex items-center justify-between gap-3 border-b border-border px-6 py-4"
		>
			<div>
				<h2 class="text-lg font-semibold">Answers</h2>
				<p class="text-sm text-muted-foreground">
					<span class="font-mono">{participant.key}</span>
					{#if participant.label}· {participant.label}{/if}
				</p>
			</div>
			<Button variant="ghost" size="sm" onclick={onClose}>Close ✕</Button>
		</header>

		<div class="max-h-[70vh] space-y-8 overflow-y-auto px-6 py-5">
			{#if loading}
				<p class="text-sm text-muted-foreground">Loading…</p>
			{:else if error}
				<p class="text-sm text-destructive" role="alert">{error}</p>
			{:else}

				{#if sessions.length > 0}
					<section class="space-y-3">
						<h4 class="text-sm font-medium">Sessions ({sessions.length})</h4>
						<ul class="space-y-3">
							{#each sessions as s (s.id)}
								<li class="space-y-1 rounded-lg border border-border bg-muted/30 p-3">
									<div class="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
										{#if s.prolific_pid?.trim()}
											<Badge variant="outline" class="font-mono">PROLIFIC_PID: {s.prolific_pid}</Badge>
										{:else}
											<Badge variant="outline">No Prolific ID (student study)</Badge>
										{/if}
										<Badge variant="outline">{s.speed}</Badge>
										<span>{fmt(s.created_at)}</span>
										<span class="font-mono">{s.id.slice(0, 8)}</span>
									</div>
									{#if s.feature_title?.trim()}
										<p class="text-sm font-medium">{s.feature_title}</p>
									{/if}
									<p class="whitespace-pre-wrap text-sm text-muted-foreground">
										{s.description?.trim() || '—'}
									</p>
								</li>
							{/each}
						</ul>
					</section>
				{/if}

				{#if entries.length === 0}
					<p class="text-sm text-muted-foreground">
						{sessions.length > 0
							? 'This participant ran the tool but has not submitted the questionnaire yet.'
							: 'This participant has no sessions or questionnaire answers yet.'}
					</p>
				{/if}

				{#each entries as entry, i (entry.id)}
					<section class="space-y-5">
						{#if entries.length > 1}
							<h3 class="text-xs font-medium uppercase tracking-wide text-muted-foreground">
								Submission {entries.length - i}
							</h3>
						{/if}

						<div class="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
							<Badge variant="outline">{entry.mode}</Badge>
							<span>Submitted {fmt(entry.created_at)}</span>
							{#if entry.session_id_fast}
								<span class="font-mono">fast: {entry.session_id_fast.slice(0, 8)}</span>
							{/if}
							{#if entry.session_id_thinking}
								<span class="font-mono">thinking: {entry.session_id_thinking.slice(0, 8)}</span>
							{/if}
							{#if entry.prolific_pid?.trim()}
								<Badge variant="outline" class="font-mono">PROLIFIC_PID: {entry.prolific_pid}</Badge>
							{/if}
						</div>

						{#if entry.description?.trim() || entry.feature_title?.trim()}
							<div class="space-y-1 rounded-lg border border-border bg-muted/30 p-3">
								<p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">
									Feature prompt
								</p>
								{#if entry.feature_title?.trim()}
									<p class="text-sm font-medium">{entry.feature_title}</p>
								{/if}
								<p class="whitespace-pre-wrap text-sm text-muted-foreground">
									{entry.description?.trim() || '—'}
								</p>
							</div>
						{/if}

						<div class="space-y-3">
							<h4 class="text-sm font-medium">Rating questions</h4>
							<ul class="space-y-3">
								{#each LIKERT_QUESTIONS as q (q.id)}
									{@const value = entry.likert[q.id] ?? null}
									<li class="space-y-1">
										<p class="text-sm text-muted-foreground">
											{questionText(entry, q.id, q.text)}
										</p>
										<p class="text-sm font-medium">
											{#if value === null}
												<span class="text-muted-foreground">Did not use</span>
											{:else}
												{value} — {scaleLabel(value)}
											{/if}
										</p>
									</li>
								{/each}
							</ul>
						</div>

						<div class="space-y-3">
							<h4 class="text-sm font-medium">Open-ended answers</h4>
							<ul class="space-y-3">
								{#each OPEN_QUESTIONS as q (q.id)}
									{@const answer = entry.open[q.id]?.trim()}
									<li class="space-y-1">
										<p class="text-sm text-muted-foreground">
											{questionText(entry, q.id, q.label)}
										</p>
										<p class="whitespace-pre-wrap text-sm">
											{#if answer}{answer}{:else}<span class="text-muted-foreground">—</span>{/if}
										</p>
									</li>
								{/each}
							</ul>
						</div>

						<div class="space-y-3">
							<h4 class="text-sm font-medium">About the participant</h4>
							<dl class="grid grid-cols-1 gap-2 sm:grid-cols-2">
								{#each DEMOGRAPHIC_QUESTIONS as q (q.id)}
									{@const answer = entry.demographics[q.id]?.trim()}
									<div class="space-y-0.5">
										<dt class="text-xs text-muted-foreground">
											{questionText(entry, q.id, q.question)}
										</dt>
										<dd class="text-sm">
											{#if answer}{answer}{:else}<span class="text-muted-foreground">—</span>{/if}
										</dd>
									</div>
								{/each}
							</dl>
						</div>
					</section>

					{#if i < entries.length - 1}
						<hr class="border-border" />
					{/if}
				{/each}
			{/if}
		</div>
	</div>
</div>
