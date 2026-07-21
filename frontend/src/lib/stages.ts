import { DIMENSIONS } from '$lib/api';
import { session } from '$lib/stores/session.svelte';

export const STAGES = [
	{ key: 'describe', label: 'Describe', path: '/' },
	{ key: 'reflections', label: 'Reflections', path: '/reflections' },
	{ key: 'explore', label: 'Explore', path: '/explore' },
	{ key: 'export', label: 'Export', path: '/export' },
	{ key: 'feedback', label: 'Feedback', path: '/feedback' }
] as const;

export type Stage = (typeof STAGES)[number];

export function reflectionsComplete(): boolean {
	const total = DIMENSIONS.length;
	const { fast, thinking } = session.state.variants;
	if (session.state.compare) {
		return fast.reflections.length >= total && thinking.reflections.length >= total;
	}
	return session.state.variants[session.state.view].reflections.length >= total;
}

export function canVisit(path: string): boolean {
	if (path === '/') return true;

	if (path === '/feedback') return reflectionsComplete();

	const { fast, thinking } = session.state.variants;
	return fast.reflections.length > 0 || thinking.reflections.length > 0;
}

export function previousStagePath(pathname: string): string | null {
	const idx = STAGES.findIndex((s) => s.path === pathname);
	if (idx <= 0) return null;
	for (let i = idx - 1; i >= 0; i--) {
		const stage = STAGES[i];
		if (canVisit(stage.path)) return stage.path;
	}
	return null;
}
