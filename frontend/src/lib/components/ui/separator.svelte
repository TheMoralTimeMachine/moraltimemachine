<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	import { cn } from '$lib/utils';

	interface Props extends HTMLAttributes<HTMLDivElement> {
		class?: string;
		orientation?: 'horizontal' | 'vertical';
	}

	let { class: className, orientation = 'horizontal', ...rest }: Props = $props();
</script>

<div
	role="separator"
	aria-orientation={orientation}
	class={cn('shrink-0 bg-foreground/15', orientation === 'horizontal' ? 'h-px w-full' : 'h-full w-px', className)}
	{...rest}
></div>
