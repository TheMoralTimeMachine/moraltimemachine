<script lang="ts">
	import type { LucideIcon } from '@lucide/svelte';
	import { type HarmCategory, type HarmRef, HARM_META } from '$lib/api';
	import Tooltip from './ui/tooltip.svelte';
	import Lock from '@lucide/svelte/icons/lock';
	import UserX from '@lucide/svelte/icons/user-x';
	import Bug from '@lucide/svelte/icons/bug';
	import Flag from '@lucide/svelte/icons/flag';
	import Eye from '@lucide/svelte/icons/eye';
	import Newspaper from '@lucide/svelte/icons/newspaper';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import Scale from '@lucide/svelte/icons/scale';
	import VenetianMask from '@lucide/svelte/icons/venetian-mask';
	import Gavel from '@lucide/svelte/icons/gavel';

	interface HarmStyle {
		text: string;
		bg: string;
		icon: LucideIcon;
	}

	const HARM_COLORS: Record<HarmCategory, HarmStyle> = {

		Privacy: { text: '#f09595', bg: 'rgba(226, 75, 74, 0.16)', icon: Lock },
		'Fraudulent activity': { text: '#f0997b', bg: 'rgba(216, 90, 48, 0.18)', icon: UserX },
		'Disruptive activity': { text: '#efaa4a', bg: 'rgba(239, 159, 39, 0.16)', icon: Bug },
		'Inappropriate content': { text: '#ed93b1', bg: 'rgba(212, 83, 126, 0.16)', icon: Flag },

		Transparency: { text: '#85b7eb', bg: 'rgba(55, 138, 221, 0.16)', icon: Eye },
		'False information': { text: '#e6c34a', bg: 'rgba(214, 178, 39, 0.16)', icon: Newspaper },
		Censorship: { text: '#97c459', bg: 'rgba(99, 153, 34, 0.18)', icon: EyeOff },

		Disparity: { text: '#a5a0f0', bg: 'rgba(120, 110, 230, 0.18)', icon: Scale },
		Manipulation: { text: '#c993e6', bg: 'rgba(168, 95, 205, 0.22)', icon: VenetianMask },
		Accountability: { text: '#bcb2cf', bg: 'rgba(150, 135, 175, 0.18)', icon: Gavel }
	};

	interface Props {

		harm: HarmCategory | HarmRef;
	}

	let { harm }: Props = $props();

	const category = $derived(typeof harm === 'string' ? harm : harm.category);
	const explanation = $derived(typeof harm === 'string' ? '' : harm.explanation);
	const c = $derived(HARM_COLORS[category]);
	const Icon = $derived(c.icon);

	const tip = $derived(explanation || HARM_META[category].description);
</script>

<Tooltip content={tip}>

	<span
		class="inline-flex cursor-help items-center gap-1.5 whitespace-nowrap rounded-full px-[11px] py-[5px] text-xs font-medium"
		style="background:{c.bg};color:{c.text};"
		tabindex="0"
		aria-label="{category}: {tip}"
	>
		<Icon size={14} />
		{category}
	</span>
</Tooltip>
