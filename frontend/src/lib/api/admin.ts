import { admin } from '$lib/stores/admin.svelte';

export interface AdminParticipant {
	key: string;
	label: string;
	created_at: string;
	revoked_at: string | null;
	session_count: number;
	feedback_count: number;
	last_session_at: string | null;
}

export interface AdminFeedbackEntry {
	id: number;
	mode: 'fast' | 'thinking' | 'compare';
	session_id_fast: string | null;
	session_id_thinking: string | null;
	created_at: string;
	description: string;
	feature_title: string;

	prolific_pid: string;
	likert: Record<string, number | null>;
	open: Record<string, string>;
	demographics: Record<string, string>;
	questions: Record<string, string>;
}

export interface AdminSession {
	id: string;
	speed: string;
	description: string;
	feature_title: string;
	prolific_pid: string;
	created_at: string;
}

export class AdminUnauthorizedError extends Error {}

function baseUrl(): string {
	const url = import.meta.env.VITE_API_BASE_URL;
	if (!url) throw new Error('VITE_API_BASE_URL is not set');
	return url.replace(/\/$/, '');
}

function headers(): Record<string, string> {
	return admin.key ? { 'X-Admin-Key': admin.key } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
	const res = await fetch(`${baseUrl()}${path}`, {
		...init,
		headers: {
			'Content-Type': 'application/json',
			...headers(),
			...init?.headers
		}
	});
	if (!res.ok) {
		if (res.status === 401) {
			admin.clear();
			throw new AdminUnauthorizedError('admin key rejected');
		}
		const text = await res.text().catch(() => '');
		throw new Error(`API ${res.status} ${res.statusText}: ${text}`);
	}
	return res.json();
}

export async function checkAdmin(key: string): Promise<'ok' | 'invalid' | 'disabled'> {
	const res = await fetch(`${baseUrl()}/api/admin/check`, {
		headers: { 'X-Admin-Key': key }
	});
	if (res.status === 401) return 'invalid';
	if (res.status === 403) return 'disabled';
	if (!res.ok) {
		const text = await res.text().catch(() => '');
		throw new Error(`API ${res.status} ${res.statusText}: ${text}`);
	}
	return 'ok';
}

export function listKeys(): Promise<{ participants: AdminParticipant[] }> {
	return request('/api/admin/keys');
}

export function getFeedback(key: string): Promise<{ feedback: AdminFeedbackEntry[] }> {
	return request(`/api/admin/keys/${encodeURIComponent(key)}/feedback`);
}

export function getSessions(key: string): Promise<{ sessions: AdminSession[] }> {
	return request(`/api/admin/keys/${encodeURIComponent(key)}/sessions`);
}

export function mintKeys(count: number, label: string): Promise<{ keys: string[] }> {
	return request('/api/admin/keys', {
		method: 'POST',
		body: JSON.stringify({ count, label })
	});
}

export function revokeKey(key: string): Promise<{ ok: boolean }> {
	return request(`/api/admin/keys/${encodeURIComponent(key)}/revoke`, {
		method: 'POST'
	});
}

export function restoreKey(key: string): Promise<{ ok: boolean }> {
	return request(`/api/admin/keys/${encodeURIComponent(key)}/restore`, {
		method: 'POST'
	});
}

export async function downloadExport(): Promise<void> {
	const res = await fetch(`${baseUrl()}/api/admin/export`, {
		headers: headers()
	});
	if (!res.ok) {
		if (res.status === 401) {
			admin.clear();
			throw new AdminUnauthorizedError('admin key rejected');
		}
		const text = await res.text().catch(() => '');
		throw new Error(`API ${res.status} ${res.statusText}: ${text}`);
	}
	const blob = await res.blob();
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = `mtm-study-export-${new Date().toISOString().slice(0, 10)}.zip`;
	document.body.appendChild(a);
	a.click();
	a.remove();
	URL.revokeObjectURL(url);
}
