<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { isBackupSessionId, streamBackupReply } from '$lib/api/backup';
	import { session } from '$lib/stores/session.svelte';
	import Button from '$lib/components/ui/button.svelte';
	import Textarea from '$lib/components/ui/textarea.svelte';
	import ChatMessage from '$lib/components/chat-message.svelte';
	import BackButton from '$lib/components/back-button.svelte';
	import VariantSwitcher from '$lib/components/variant-switcher.svelte';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';

	const WELCOME = "I've generated reflections for your feature. What would you like to explore further?";

	const STARTERS = [
		'What are the 3 most serious risks here, and why?',
		'Which mitigation should we prioritize first?',
		'Which stakeholder group is hit hardest?',
		'Draft a safer version of this feature description'
	];

	let composer = $state('');
	let listEl: HTMLDivElement | undefined = $state();

	const reflections = $derived(session.active.reflections);
	const loadingChat = $derived(session.state.loading.chat);

	$effect(() => {
		const v = session.active;
		if (v.reflections.length > 0 && v.chat.length === 0) {
			v.chat.push({ role: 'assistant', content: WELCOME });
			session.save();
		}
	});

	const riskCount = $derived(reflections.reduce((n, r) => n + r.points.length, 0));
	const mitigationCount = $derived.by(() => {
		const set = new Set<string>();
		for (const r of reflections) {
			if (r.mitigation?.trim()) set.add(r.mitigation.trim().toLowerCase());
			for (const p of r.points) if (p.mitigation?.trim()) set.add(p.mitigation.trim().toLowerCase());
		}
		return set.size;
	});

	onMount(() => {
		if (session.active.reflections.length === 0) {
			goto('/', { replaceState: true });
			return;
		}
		scrollToBottom();

		const q = new URLSearchParams(window.location.search).get('q');
		if (q) {
			goto('/explore', { replaceState: true });
			send(q);
		}
	});

	async function scrollToBottom() {
		await tick();
		listEl?.scrollTo({ top: listEl.scrollHeight, behavior: 'smooth' });
	}

	async function send(explicit?: string) {
		const text = (explicit ?? composer).trim();

		const variant = session.active;
		if (!text || !variant.sessionId || session.state.loading.chat) return;
		if (explicit === undefined) composer = '';
		variant.chat.push({ role: 'user', content: text });

		variant.chat.push({ role: 'assistant', content: '', sources: [] });
		const idx = variant.chat.length - 1;
		session.state.loading.chat = true;
		session.save();
		scrollToBottom();
		try {
			await (isBackupSessionId(variant.sessionId)
				? streamBackupReply(
						text,
						(delta) => {
							variant.chat[idx].content += delta;
							scrollToBottom();
						},
						(sources) => {
							variant.chat[idx].sources = sources;
						}
					)
				: api.sendMessageStream(
						variant.sessionId,
						text,
						(delta) => {
							variant.chat[idx].content += delta;
							scrollToBottom();
						},
						(sources) => {
							variant.chat[idx].sources = sources;
						}
					));
		} catch (e) {
			variant.chat[idx].content = e instanceof Error ? `(error: ${e.message})` : '(error)';
		} finally {
			session.state.loading.chat = false;
			session.save();
			scrollToBottom();
		}
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			send();
		}
	}
</script>

<div class="mx-auto flex min-h-[calc(100vh-8rem)] w-full max-w-3xl flex-col gap-5">
	<div class="flex items-center justify-between">
		<BackButton />
		<Button variant="ghost" size="sm" onclick={() => goto('/export')}>Continue to Export →</Button>
	</div>

	<header class="space-y-2">
		<div class="flex items-center gap-2">
			<span class="h-1.5 w-1.5 rounded-full" style="background: var(--color-tomorrow)"></span>
			<span class="text-sm font-semibold" style="color: var(--color-tomorrow)">Explore deeper</span>
		</div>
		<h1 class="text-2xl font-semibold">{session.active.featureTitle || 'This feature'}</h1>
		<p class="text-sm text-muted-foreground">
			Grounded in this session's four reflections · {riskCount} risks · {mitigationCount} mitigations
		</p>
		<VariantSwitcher />
	</header>

	<div class="flex flex-wrap gap-2">
		{#each STARTERS as s}
			<button
				type="button"
				onclick={() => send(s)}
				disabled={loadingChat}
				class="rounded-full border border-border bg-card px-4 py-2 text-sm text-foreground/90 transition-colors hover:bg-accent hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
			>
				{s}
			</button>
		{/each}
	</div>

	<div bind:this={listEl} class="flex-1 space-y-6 overflow-y-auto py-2">
		{#each session.active.chat as message, i (i)}
			<ChatMessage {message} />
		{/each}
	</div>

	<div class="pt-1">
		<div class="flex items-end gap-2">
			<Textarea
				bind:value={composer}
				rows={1}
				placeholder="Ask about the risks, mitigations, or try a what-if…"
				onkeydown={onKeydown}
				class="min-h-[52px] flex-1 resize-none rounded-2xl bg-card px-4 py-3.5 text-sm"
			/>
			<Button
				onclick={() => send()}
				disabled={!composer.trim() || loadingChat}
				class="h-[52px] w-[52px] shrink-0 rounded-2xl p-0"
				aria-label="Send"
			>
				<ArrowUp size={18} />
			</Button>
		</div>
	</div>
</div>
