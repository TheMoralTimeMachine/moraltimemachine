<script lang="ts">
	import type { ChatMessage } from '$lib/api';
	import { renderMarkdown } from '$lib/markdown';
	import FileText from '@lucide/svelte/icons/file-text';

	interface Props {
		message: ChatMessage;
	}

	let { message }: Props = $props();

	const isUser = $derived(message.role === 'user');

	const html = $derived(message.content ? renderMarkdown(message.content) : '');
</script>

{#if isUser}
	<div class="flex justify-end">
		<div
			class="max-w-[85%] rounded-2xl border px-4 py-2.5 text-sm text-foreground"
			style="border-color: color-mix(in oklch, var(--color-tomorrow), transparent 62%); background: color-mix(in oklch, var(--color-tomorrow), transparent 90%);"
		>
			{message.content}
		</div>
	</div>
{:else}
	<div class="space-y-3">
		{#if message.content}

			<div class="chat-markdown text-sm leading-7 text-foreground/85">{@html html}</div>
		{:else}
			<div class="flex gap-1 py-1" aria-label="Thinking">
				<span class="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]"></span>
				<span class="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]"></span>
				<span class="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground"></span>
			</div>
		{/if}

		{#if message.sources?.length}
			<div class="flex flex-wrap items-center gap-1.5">
				<span class="text-[11px] text-muted-foreground">Grounded in</span>
				{#each message.sources as src (src.source)}
					<span
						class="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-2.5 py-1 text-[11px] text-muted-foreground"
						title={src.title}
					>
						<FileText size={12} aria-hidden="true" />
						{src.title}
					</span>
				{/each}
			</div>
		{/if}
	</div>
{/if}

<style>
	.chat-markdown :global(> *:first-child) {
		margin-top: 0;
	}
	.chat-markdown :global(> *:last-child) {
		margin-bottom: 0;
	}
	.chat-markdown :global(p) {
		margin: 0.5rem 0;
	}
	.chat-markdown :global(strong) {
		font-weight: 600;
		color: var(--color-foreground);
	}
	.chat-markdown :global(em) {
		font-style: italic;
	}
	.chat-markdown :global(h1),
	.chat-markdown :global(h2),
	.chat-markdown :global(h3),
	.chat-markdown :global(h4) {
		margin: 1rem 0 0.4rem;
		font-weight: 600;
		line-height: 1.3;
		color: var(--color-foreground);
	}
	.chat-markdown :global(h1) {
		font-size: 1.05rem;
	}
	.chat-markdown :global(h2) {
		font-size: 1rem;
	}
	.chat-markdown :global(h3),
	.chat-markdown :global(h4) {
		font-size: 0.9rem;
	}
	.chat-markdown :global(ul),
	.chat-markdown :global(ol) {
		margin: 0.5rem 0;
		padding-left: 1.4rem;
	}
	.chat-markdown :global(ul) {
		list-style: disc;
	}
	.chat-markdown :global(ol) {
		list-style: decimal;
	}
	.chat-markdown :global(li) {
		margin: 0.2rem 0;
	}
	.chat-markdown :global(li::marker) {
		color: var(--color-muted-foreground);
	}
	.chat-markdown :global(a) {
		color: var(--color-tomorrow);
		text-decoration: underline;
		text-underline-offset: 2px;
	}
	.chat-markdown :global(code) {
		font-size: 0.85em;
		padding: 0.1rem 0.3rem;
		border-radius: 0.3rem;
		background: color-mix(in oklch, var(--color-foreground), transparent 92%);
	}
	.chat-markdown :global(pre) {
		margin: 0.5rem 0;
		padding: 0.7rem 0.85rem;
		border-radius: 0.6rem;
		overflow-x: auto;
		background: color-mix(in oklch, var(--color-foreground), transparent 94%);
	}
	.chat-markdown :global(pre code) {
		padding: 0;
		background: transparent;
	}
	.chat-markdown :global(blockquote) {
		margin: 0.5rem 0;
		padding-left: 0.8rem;
		border-left: 2px solid var(--color-border);
		color: var(--color-muted-foreground);
	}
	.chat-markdown :global(hr) {
		margin: 0.9rem 0;
		border: none;
		border-top: 1px solid var(--color-border);
	}
</style>
