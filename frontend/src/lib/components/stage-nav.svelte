<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { STAGES, canVisit } from '$lib/stages';
	import { cn } from '$lib/utils';
	import Hourglass from '@lucide/svelte/icons/hourglass';
	import Moon from '@lucide/svelte/icons/moon';
	import Sun from '@lucide/svelte/icons/sun';
	import { mode, toggleMode } from 'mode-watcher';

	let scrollY = $state(0);

	const scrolled = $derived(scrollY > 50);

	function handleClick(path: string, enabled: boolean, e: MouseEvent) {
		e.preventDefault();
		if (!enabled) return;
		goto(path);
	}
</script>

<svelte:window bind:scrollY />

<header class="nav no-print" class:scrolled style="height: var(--nav-height);">
	<div class="mx-auto grid h-full max-w-5xl grid-cols-[auto_1fr_auto] items-center gap-2 px-3 sm:grid-cols-[1fr_auto_1fr] sm:px-6">
		<a href="/" class="flex items-center gap-2.5 justify-self-start font-semibold">
			<span class="flex h-[22px] w-[22px] items-center justify-center rounded-md bg-accent text-foreground">
				<Hourglass size={13} aria-hidden="true" />
			</span>
			<span class="hidden text-sm text-foreground sm:inline">Moral Time Machine</span>
		</a>

		<nav
			aria-label="Primary"
			class="no-scrollbar flex min-w-0 items-center gap-0.5 justify-self-center overflow-x-auto rounded-full border border-border bg-accent p-1"
		>
			{#each STAGES as stage}

				{@const active =
					$page.url.pathname === stage.path || (stage.path !== '/' && $page.url.pathname.startsWith(stage.path + '/'))}
				{@const enabled = canVisit(stage.path)}
				{@const feedback = stage.key === 'feedback'}
				<a
					href={stage.path}
					onclick={(e) => handleClick(stage.path, enabled, e)}
					aria-current={active ? 'page' : undefined}
					aria-disabled={!enabled || undefined}
					class={cn(
						'relative shrink-0 rounded-full px-2.5 py-1.5 text-[13px] transition-colors sm:px-4',
						active && 'font-medium text-primary-foreground',

						!active &&
							enabled &&
							feedback &&
							'border border-amber-500/40 bg-amber-500/10 font-medium text-amber-600 hover:bg-amber-500/20 dark:text-amber-400',
						!active && enabled && !feedback && 'text-muted-foreground hover:bg-background hover:text-foreground',
						!enabled && 'cursor-not-allowed text-muted-foreground/50'
					)}
				>
					{#if active}
						<span class="bubble absolute inset-0 rounded-full bg-primary" aria-hidden="true"></span>
					{/if}
					<span class="relative z-10">{stage.label}</span>
				</a>
			{/each}
		</nav>

		<button
			type="button"
			onclick={toggleMode}
			aria-label="Toggle dark mode"
			title="Toggle dark mode"
			class="flex h-8 w-8 items-center justify-center justify-self-end rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
		>
			{#if mode.current === 'dark'}
				<Sun class="h-4 w-4" />
			{:else}
				<Moon class="h-4 w-4" />
			{/if}
		</button>
	</div>
</header>

<style>
	.nav {
		position: sticky;
		top: 0;
		z-index: 50;
		background: transparent;
		border-bottom: 1px solid transparent;
		transition:
			background-color 0.3s ease,
			border-color 0.3s ease;

		view-transition-name: nav-header;
	}

	.bubble {
		view-transition-name: nav-bubble;
	}
	:global(::view-transition-group(nav-bubble)) {
		animation-duration: 0.3s;
		animation-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
	}

	.no-scrollbar {
		scrollbar-width: none;
		-ms-overflow-style: none;
	}
	.no-scrollbar::-webkit-scrollbar {
		display: none;
	}
	.nav.scrolled {
		background: color-mix(in oklch, var(--color-card), transparent 30%);
		-webkit-backdrop-filter: blur(12px);
		backdrop-filter: blur(12px);
		border-bottom-color: var(--color-border);
	}
</style>
