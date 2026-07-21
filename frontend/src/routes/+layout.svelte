<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { onNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import { ModeWatcher } from 'mode-watcher';
	import { session } from '$lib/stores/session.svelte';
	import { participant } from '$lib/stores/participant.svelte';
	import { prolific } from '$lib/stores/prolific.svelte';
	import StageNav from '$lib/components/stage-nav.svelte';
	import KeyGate from '$lib/components/key-gate.svelte';
	import type { Snippet } from 'svelte';

	interface Props {
		children: Snippet;
	}

	let { children }: Props = $props();

	const useRealApi = Boolean(import.meta.env.VITE_API_BASE_URL);
	let hydrated = $state(false);

	const isAdminRoute = $derived(page.url.pathname.startsWith('/admin'));

	onMount(() => {
		session.hydrate();
		participant.hydrate();
		prolific.hydrate();
		hydrated = true;
	});

	onNavigate((navigation) => {
		if (!document.startViewTransition) return;
		return new Promise((resolve) => {
			document.startViewTransition(async () => {
				resolve();
				await navigation.complete;
			});
		});
	});
</script>

<ModeWatcher />

{#if useRealApi && hydrated && !participant.key && !isAdminRoute}
	<KeyGate />
{:else}
	<div class="flex min-h-screen flex-col overflow-x-clip">
		<StageNav />
		<main class="mx-auto w-full max-w-5xl flex-1 px-6 py-8">
			{@render children()}
		</main>
	</div>
{/if}
