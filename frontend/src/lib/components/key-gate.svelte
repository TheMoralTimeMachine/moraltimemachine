<script lang="ts">
	import { api } from '$lib/api';
	import { BACKUP_PARTICIPANT_KEY, isBackupTrigger, markBackupAutoStart } from '$lib/api/backup';
	import Button from '$lib/components/ui/button.svelte';
	import Card from '$lib/components/ui/card.svelte';
	import Input from '$lib/components/ui/input.svelte';
	import { participant } from '$lib/stores/participant.svelte';

	let key = $state('');
	let checking = $state(false);
	let error = $state<string | null>(null);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		const candidate = key.trim();
		if (!candidate || checking) return;

		if (isBackupTrigger(candidate)) {
			error = null;
			markBackupAutoStart();
			participant.setKey(BACKUP_PARTICIPANT_KEY);
			return;
		}

		checking = true;
		error = null;
		try {
			if (await api.checkAuth(candidate)) {
				participant.setKey(candidate);
			} else {
				error = "That key wasn't recognized. Check for typos — keys look like mtm-xxx-xxx-xxx.";
			}
		} catch {
			error = 'Could not reach the server. Please try again in a moment.';
		} finally {
			checking = false;
		}
	}
</script>

<div class="flex min-h-screen items-center justify-center px-6">
	<Card class="w-full max-w-md space-y-5 p-8">
		<div class="space-y-2 text-center">
			<div class="text-3xl">🕰️</div>
			<h1 class="text-xl font-semibold">Moral Time Machine</h1>
			<p class="text-sm text-muted-foreground">
				This study build is restricted to invited participants. Enter the password you received to begin. You don't need
				a username.
			</p>
		</div>
		<form class="space-y-3" onsubmit={submit}>
			<Input
				bind:value={key}
				placeholder="mtm-xxx-xxx-xxx"
				autocomplete="off"
				autocapitalize="off"
				spellcheck={false}
				aria-label="Participant key"
			/>
			{#if error}
				<p class="text-sm text-destructive" role="alert">{error}</p>
			{/if}
			<Button type="submit" class="w-full" disabled={!key.trim() || checking}>
				{checking ? 'Checking…' : 'Enter study'}
			</Button>
		</form>
	</Card>
</div>
