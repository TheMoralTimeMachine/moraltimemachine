<script lang="ts">
	import type { Snippet } from 'svelte';
	import { cn } from '$lib/utils';

	interface Props {

		content: string;

		children: Snippet;

		class?: string;
	}

	let { content, children, class: className }: Props = $props();

	let open = $state(false);
	let trigger: HTMLSpanElement;

	let x = $state(0);
	let y = $state(0);

	function show() {
		const r = trigger.getBoundingClientRect();
		x = r.left + r.width / 2;
		y = r.top;
		open = true;
	}

	function hide() {
		open = false;
	}

	function portal(node: HTMLElement) {
		document.body.appendChild(node);
		const close = () => (open = false);
		window.addEventListener('scroll', close, true);
		window.addEventListener('resize', close);
		return {
			destroy() {
				window.removeEventListener('scroll', close, true);
				window.removeEventListener('resize', close);
				node.remove();
			}
		};
	}
</script>

<span
	bind:this={trigger}
	class={cn('inline-flex', className)}
	onmouseenter={show}
	onmouseleave={hide}
	onfocusin={show}
	onfocusout={hide}
	role="presentation"
>
	{@render children()}
</span>

{#if open}
	<span
		use:portal
		role="tooltip"
		class="pointer-events-none fixed z-50 w-max max-w-[18rem] -translate-x-1/2 -translate-y-full
           rounded-md border border-border bg-popover px-3 py-2 text-xs leading-relaxed
           text-popover-foreground shadow-md"
		style="left:{x}px;top:{y - 8}px;"
	>
		{content}

		<span
			class="absolute left-1/2 top-full h-2 w-2 -translate-x-1/2 -translate-y-1/2 rotate-45
             border-b border-r border-border bg-popover"
		></span>
	</span>
{/if}
