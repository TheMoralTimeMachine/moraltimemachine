import type { LucideIcon } from '@lucide/svelte';
import Zap from '@lucide/svelte/icons/zap';
import Hourglass from '@lucide/svelte/icons/hourglass';
import Search from '@lucide/svelte/icons/search';
import Users from '@lucide/svelte/icons/users';
import type { Dimension } from './api';

export const DIMENSION_ICONS: Record<Dimension, LucideIcon> = {
	tomorrow: Zap,
	in_five_years: Hourglass,
	public_scrutiny: Search,
	stakeholder_impact: Users
};
