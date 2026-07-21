<script lang="ts">
	import type { Speed } from '$lib/api';
	import { session } from '$lib/stores/session.svelte';
	import Zap from '@lucide/svelte/icons/zap';
	import ListOrdered from '@lucide/svelte/icons/list-ordered';

	const options: { value: Speed; label: string; icon: typeof Zap }[] = [
		{ value: 'fast', label: 'Fast', icon: Zap },
		{ value: 'thinking', label: 'Thinking', icon: ListOrdered }
	];

	function select(s: Speed) {
		if (session.state.view === s) return;
		session.state.view = s;
		session.save();
	}
</script>

{#if session.state.compare}
	<div class="flex flex-wrap items-center gap-2 no-print">
		<span class="text-xs font-medium text-muted-foreground">Comparing</span>
		<div
			class="inline-flex rounded-full border border-border bg-muted/40 p-0.5"
			role="radiogroup"
			aria-label="Compare strategy"
		>
			{#each options as opt (opt.value)}
				{@const Icon = opt.icon}
				{@const active = session.state.view === opt.value}
				<button
					type="button"
					role="radio"
					aria-checked={active}
					onclick={() => select(opt.value)}
					class={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
						active ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
					}`}
				>
					<Icon size={13} />
					<span>{opt.label}</span>
				</button>
			{/each}
		</div>
	</div>
{/if}
