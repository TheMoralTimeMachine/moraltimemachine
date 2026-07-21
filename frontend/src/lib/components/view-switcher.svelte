<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import ChartColumn from '@lucide/svelte/icons/chart-column';
	import LayoutGrid from '@lucide/svelte/icons/layout-grid';

	const options = [
		{ path: '/reflections', label: 'Cards', icon: LayoutGrid },
		{ path: '/reflections/insights', label: 'Insights', icon: ChartColumn }
	] as const;
</script>

<div class="flex flex-wrap items-center gap-2 no-print">
	<span class="text-xs font-medium text-muted-foreground">View</span>
	<div class="inline-flex rounded-full border border-border bg-muted/40 p-0.5">
		{#each options as opt (opt.path)}
			{@const Icon = opt.icon}
			{@const active = $page.url.pathname === opt.path}
			<a
				href={opt.path}
				aria-current={active ? 'page' : undefined}
				onclick={(e) => {
					e.preventDefault();
					if (!active) goto(opt.path);
				}}
				class={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
					active ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
				}`}
			>
				<Icon size={13} />
				<span>{opt.label}</span>
			</a>
		{/each}
	</div>
</div>
