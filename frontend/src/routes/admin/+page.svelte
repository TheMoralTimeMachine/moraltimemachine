<script lang="ts">
	import { onMount } from 'svelte';
	import {
		AdminUnauthorizedError,
		checkAdmin,
		downloadExport,
		getFeedback,
		getSessions,
		listKeys,
		mintKeys,
		restoreKey,
		revokeKey,
		type AdminFeedbackEntry,
		type AdminParticipant,
		type AdminSession
	} from '$lib/api/admin';
	import { admin } from '$lib/stores/admin.svelte';
	import Card from '$lib/components/ui/card.svelte';
	import Input from '$lib/components/ui/input.svelte';
	import Button from '$lib/components/ui/button.svelte';
	import Badge from '$lib/components/ui/badge.svelte';
	import AdminAnswers from '$lib/components/admin-answers.svelte';

	const useRealApi = Boolean(import.meta.env.VITE_API_BASE_URL);
	let hydrated = $state(false);

	let gateKey = $state('');
	let gateChecking = $state(false);
	let gateError = $state<string | null>(null);

	let participants = $state<AdminParticipant[]>([]);
	let loadError = $state<string | null>(null);
	let busyKey = $state<string | null>(null);

	let mintCount = $state('5');
	let mintLabel = $state('');
	let minting = $state(false);
	let minted = $state<string[]>([]);
	let copied = $state(false);

	let exporting = $state(false);
	let actionError = $state<string | null>(null);

	let viewing = $state<AdminParticipant | null>(null);
	let answers = $state<AdminFeedbackEntry[]>([]);
	let viewSessions = $state<AdminSession[]>([]);
	let answersLoading = $state(false);
	let answersError = $state<string | null>(null);

	const stats = $derived({
		total: participants.length,
		used: participants.filter((p) => p.session_count > 0 || p.feedback_count > 0).length,
		revoked: participants.filter((p) => p.revoked_at !== null).length
	});
	const countValid = $derived(/^\d+$/.test(mintCount.trim()) && +mintCount >= 1 && +mintCount <= 200);

	onMount(() => {
		admin.hydrate();
		hydrated = true;
		if (admin.key) refresh();
	});

	function surface(e: unknown) {
		if (e instanceof AdminUnauthorizedError) return;
		actionError = e instanceof Error ? e.message : 'Something went wrong.';
	}

	async function refresh() {
		loadError = null;
		try {
			participants = (await listKeys()).participants;
		} catch (e) {
			if (!(e instanceof AdminUnauthorizedError)) loadError = 'Could not load keys.';
		}
	}

	async function unlock(event: SubmitEvent) {
		event.preventDefault();
		const candidate = gateKey.trim();
		if (!candidate || gateChecking) return;
		gateChecking = true;
		gateError = null;
		try {
			const result = await checkAdmin(candidate);
			if (result === 'ok') {
				admin.setKey(candidate);
				gateKey = '';
				await refresh();
			} else if (result === 'disabled') {
				gateError = 'Admin access is disabled on the server (MTM_ADMIN_KEY is not set).';
			} else {
				gateError = 'Wrong admin key.';
			}
		} catch {
			gateError = 'Could not reach the server. Please try again in a moment.';
		} finally {
			gateChecking = false;
		}
	}

	async function mint(event: SubmitEvent) {
		event.preventDefault();
		if (!countValid || minting) return;
		minting = true;
		actionError = null;
		copied = false;
		try {
			minted = (await mintKeys(+mintCount, mintLabel.trim())).keys;
			await refresh();
		} catch (e) {
			surface(e);
		} finally {
			minting = false;
		}
	}

	async function copyMinted() {
		try {
			await navigator.clipboard.writeText(minted.join('\n'));
			copied = true;
			setTimeout(() => (copied = false), 2000);
		} catch {

		}
	}

	async function toggleRevoked(p: AdminParticipant) {
		if (busyKey) return;
		busyKey = p.key;
		actionError = null;
		try {
			await (p.revoked_at ? restoreKey(p.key) : revokeKey(p.key));
			await refresh();
		} catch (e) {
			surface(e);
		} finally {
			busyKey = null;
		}
	}

	async function exportZip() {
		if (exporting) return;
		exporting = true;
		actionError = null;
		try {
			await downloadExport();
		} catch (e) {
			surface(e);
		} finally {
			exporting = false;
		}
	}

	async function openAnswers(p: AdminParticipant) {
		viewing = p;
		answers = [];
		viewSessions = [];
		answersError = null;
		answersLoading = true;
		try {

			const [feedback, sessions] = await Promise.all([getFeedback(p.key), getSessions(p.key)]);
			answers = feedback.feedback;
			viewSessions = sessions.sessions;
		} catch (e) {
			if (!(e instanceof AdminUnauthorizedError)) {
				answersError = 'Could not load answers.';
			}
		} finally {
			answersLoading = false;
		}
	}

	function closeAnswers() {
		viewing = null;
		answers = [];
		viewSessions = [];
		answersError = null;
	}

	function lock() {
		admin.clear();
		participants = [];
		minted = [];
		closeAnswers();
	}

	const fmt = (ts: string | null) => (ts ? ts.slice(0, 16) : '—');
</script>

<div class="mx-auto max-w-4xl space-y-6 pb-12">
	{#if !useRealApi}
		<Card class="space-y-2 p-8 text-center">
			<h1 class="text-xl font-semibold">Admin panel</h1>
			<p class="text-sm text-muted-foreground">
				The admin panel needs the real backend. Set <code>VITE_API_BASE_URL</code>
				and reload — in mock mode there is no study database to manage.
			</p>
		</Card>
	{:else if hydrated && !admin.key}
		<div class="flex justify-center pt-12">
			<Card class="w-full max-w-md space-y-5 p-8">
				<div class="space-y-2 text-center">
					<div class="text-3xl">🔐</div>
					<h1 class="text-xl font-semibold">Study admin</h1>
					<p class="text-sm text-muted-foreground">
						Enter the researcher admin key (<code>MTM_ADMIN_KEY</code>) to manage participant keys and export the study
						data.
					</p>
				</div>
				<form class="space-y-3" onsubmit={unlock}>
					<Input
						bind:value={gateKey}
						type="password"
						placeholder="Admin key"
						autocomplete="off"
						aria-label="Admin key"
					/>
					{#if gateError}
						<p class="text-sm text-destructive" role="alert">{gateError}</p>
					{/if}
					<Button type="submit" class="w-full" disabled={!gateKey.trim() || gateChecking}>
						{gateChecking ? 'Checking…' : 'Unlock'}
					</Button>
				</form>
			</Card>
		</div>
	{:else if admin.key}
		<header class="flex flex-wrap items-center justify-between gap-3">
			<div>
				<h1 class="text-2xl font-semibold">Study admin</h1>
				<p class="text-sm text-muted-foreground">
					{stats.total} keys · {stats.used} used · {stats.revoked} revoked
				</p>
			</div>
			<div class="flex gap-2">
				<Button onclick={exportZip} disabled={exporting}>
					{exporting ? 'Exporting…' : '⬇ Export data (.zip)'}
				</Button>
				<Button variant="outline" onclick={lock}>Lock</Button>
			</div>
		</header>

		{#if actionError}
			<p class="text-sm text-destructive" role="alert">{actionError}</p>
		{/if}

		<Card class="space-y-4 p-6">
			<h2 class="text-sm font-medium">Generate keys</h2>
			<form class="flex flex-wrap items-end gap-3" onsubmit={mint}>
				<div class="space-y-1">
					<label class="text-xs text-muted-foreground" for="mint-count">Count (1–200)</label>
					<Input id="mint-count" bind:value={mintCount} inputmode="numeric" class="w-28" />
				</div>
				<div class="flex-1 space-y-1">
					<label class="text-xs text-muted-foreground" for="mint-label">Batch label (optional)</label>
					<Input id="mint-label" bind:value={mintLabel} placeholder="e.g. pilot, round1" />
				</div>
				<Button type="submit" disabled={!countValid || minting}>
					{minting ? 'Generating…' : 'Generate'}
				</Button>
			</form>
			{#if minted.length > 0}
				<div class="space-y-2 rounded-md border border-border bg-accent/40 p-4">
					<div class="flex items-center justify-between">
						<p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">
							{minted.length} new {minted.length === 1 ? 'key' : 'keys'} — copy them now
						</p>
						<Button variant="outline" size="sm" onclick={copyMinted}>
							{copied ? 'Copied ✓' : 'Copy all'}
						</Button>
					</div>
					<pre class="overflow-x-auto font-mono text-sm leading-6">{minted.join('\n')}</pre>
				</div>
			{/if}
		</Card>

		<Card class="p-6">
			<div class="mb-4 flex items-center justify-between">
				<h2 class="text-sm font-medium">Participant keys</h2>
				<Button variant="ghost" size="sm" onclick={refresh}>Refresh</Button>
			</div>
			{#if loadError}
				<p class="text-sm text-destructive" role="alert">{loadError}</p>
			{:else if participants.length === 0}
				<p class="text-sm text-muted-foreground">No keys minted yet.</p>
			{:else}
				<div class="overflow-x-auto">
					<table class="w-full text-sm">
						<thead>
							<tr class="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
								<th class="py-2 pr-4 font-medium">Key</th>
								<th class="py-2 pr-4 font-medium">Label</th>
								<th class="py-2 pr-4 font-medium">Created</th>
								<th class="py-2 pr-4 text-right font-medium">Sessions</th>
								<th class="py-2 pr-4 text-right font-medium">Feedback</th>
								<th class="py-2 pr-4 font-medium">Last session</th>
								<th class="py-2 pr-4 font-medium">Status</th>
								<th class="py-2 font-medium"></th>
							</tr>
						</thead>
						<tbody>
							{#each participants as p (p.key)}
								<tr class="border-b border-border/60 {p.revoked_at ? 'opacity-60' : ''}">
									<td class="py-2 pr-4 font-mono">
										{#if p.session_count > 0 || p.feedback_count > 0}
											<button
												type="button"
												class="rounded text-left text-primary underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
												title="View this participant's sessions and answers"
												onclick={() => openAnswers(p)}
											>
												{p.key}
											</button>
										{:else}
											{p.key}
										{/if}
									</td>
									<td class="py-2 pr-4">{p.label || '—'}</td>
									<td class="py-2 pr-4 whitespace-nowrap text-muted-foreground">{fmt(p.created_at)}</td>
									<td class="py-2 pr-4 text-right tabular-nums">{p.session_count}</td>
									<td class="py-2 pr-4 text-right tabular-nums">{p.feedback_count}</td>
									<td class="py-2 pr-4 whitespace-nowrap text-muted-foreground">{fmt(p.last_session_at)}</td>
									<td class="py-2 pr-4">
										{#if p.revoked_at}
											<Badge variant="outline" class="text-destructive">Revoked</Badge>
										{:else if p.session_count > 0 || p.feedback_count > 0}
											<Badge>Used</Badge>
										{:else}
											<Badge variant="outline">Unused</Badge>
										{/if}
									</td>
									<td class="py-2 text-right">
										<Button variant="outline" size="sm" disabled={busyKey !== null} onclick={() => toggleRevoked(p)}>
											{busyKey === p.key ? '…' : p.revoked_at ? 'Restore' : 'Revoke'}
										</Button>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		</Card>
	{/if}

	{#if viewing}
		<AdminAnswers
			participant={viewing}
			entries={answers}
			sessions={viewSessions}
			loading={answersLoading}
			error={answersError}
			onClose={closeAnswers}
		/>
	{/if}
</div>
