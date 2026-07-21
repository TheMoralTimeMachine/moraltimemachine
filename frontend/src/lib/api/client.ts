import { participant } from '$lib/stores/participant.svelte';
import { prolific } from '$lib/stores/prolific.svelte';
import type {
	ChatSource,
	CreateSessionResponse,
	FeedbackRequest,
	GetSessionResponse,
	Reflection,
	SendMessageResponse,
	Speed
} from './types';

export class OffTopicError extends Error {}

export class UnauthorizedError extends Error {}

function baseUrl(): string {
	const url = import.meta.env.VITE_API_BASE_URL;
	if (!url) throw new Error('VITE_API_BASE_URL is not set');
	return url.replace(/\/$/, '');
}

function authHeaders(): Record<string, string> {
	const key = participant.key;
	return key ? { 'X-Participant-Key': key } : {};
}

function unauthorized(): UnauthorizedError {
	participant.clear();
	return new UnauthorizedError('participant key rejected');
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
	const res = await fetch(`${baseUrl()}${path}`, {
		headers: { 'Content-Type': 'application/json', ...authHeaders() },
		...init
	});
	if (!res.ok) {
		if (res.status === 401) throw unauthorized();
		const text = await res.text().catch(() => '');
		throw new Error(`API ${res.status} ${res.statusText}: ${text}`);
	}
	return res.json();
}

export function createSession(description: string, speed: Speed = 'fast'): Promise<CreateSessionResponse> {
	return request<CreateSessionResponse>('/api/sessions', {
		method: 'POST',
		body: JSON.stringify({ description, speed, prolificPid: prolific.pid })
	});
}

function parseSseFrame(raw: string): { event: string; data: string } | null {
	let event = 'message';
	const dataLines: string[] = [];
	for (const line of raw.split('\n')) {
		const clean = line.replace(/\r$/, '');
		if (clean.startsWith('event:')) event = clean.slice(6).trim();
		else if (clean.startsWith('data:')) dataLines.push(clean.slice(5).replace(/^ /, ''));
	}
	if (dataLines.length === 0) return null;
	return { event, data: dataLines.join('\n') };
}

export async function createSessionStream(
	description: string,
	speed: Speed,
	onReflection: (reflection: Reflection) => void,
	onTitle?: (featureTitle: string) => void
): Promise<{ sessionId: string; featureTitle: string }> {
	const res = await fetch(`${baseUrl()}/api/sessions/stream`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...authHeaders() },
		body: JSON.stringify({ description, speed, prolificPid: prolific.pid })
	});
	if (!res.ok || !res.body) {
		if (res.status === 401) throw unauthorized();
		const text = await res.text().catch(() => '');
		throw new Error(`API ${res.status} ${res.statusText}: ${text}`);
	}

	const reader = res.body.getReader();
	const decoder = new TextDecoder();
	let buffer = '';
	let sessionId: string | null = null;
	let featureTitle = '';

	for (;;) {
		const { value, done } = await reader.read();
		if (done) break;
		buffer += decoder.decode(value, { stream: true });

		let sep: number;
		while ((sep = buffer.indexOf('\n\n')) !== -1) {
			const frame = parseSseFrame(buffer.slice(0, sep));
			buffer = buffer.slice(sep + 2);
			if (!frame) continue;
			if (frame.event === 'reflection') {
				onReflection(JSON.parse(frame.data) as Reflection);
			} else if (frame.event === 'title') {
				featureTitle = (JSON.parse(frame.data) as { featureTitle: string }).featureTitle;
				onTitle?.(featureTitle);
			} else if (frame.event === 'done') {
				const d = JSON.parse(frame.data) as {
					sessionId: string;
					featureTitle?: string;
				};
				sessionId = d.sessionId;
				if (d.featureTitle) featureTitle = d.featureTitle;
			} else if (frame.event === 'rejected') {
				throw new OffTopicError((JSON.parse(frame.data) as { message: string }).message);
			} else if (frame.event === 'error') {
				throw new Error((JSON.parse(frame.data) as { error: string }).error);
			}
		}
	}

	if (!sessionId) throw new Error('stream ended before the session was created');
	return { sessionId, featureTitle };
}

export function sendMessage(sessionId: string, message: string): Promise<SendMessageResponse> {
	return request<SendMessageResponse>(`/api/sessions/${encodeURIComponent(sessionId)}/messages`, {
		method: 'POST',
		body: JSON.stringify({ message })
	});
}

export async function sendMessageStream(
	sessionId: string,
	message: string,
	onDelta: (text: string) => void,
	onSources?: (sources: ChatSource[]) => void
): Promise<void> {
	const res = await fetch(`${baseUrl()}/api/sessions/${encodeURIComponent(sessionId)}/messages/stream`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...authHeaders() },
		body: JSON.stringify({ message })
	});
	if (!res.ok || !res.body) {
		if (res.status === 401) throw unauthorized();
		const text = await res.text().catch(() => '');
		throw new Error(`API ${res.status} ${res.statusText}: ${text}`);
	}

	const reader = res.body.getReader();
	const decoder = new TextDecoder();
	let buffer = '';

	for (;;) {
		const { value, done } = await reader.read();
		if (done) break;
		buffer += decoder.decode(value, { stream: true });

		let sep: number;
		while ((sep = buffer.indexOf('\n\n')) !== -1) {
			const frame = parseSseFrame(buffer.slice(0, sep));
			buffer = buffer.slice(sep + 2);
			if (!frame) continue;
			if (frame.event === 'delta') {
				onDelta((JSON.parse(frame.data) as { text: string }).text);
			} else if (frame.event === 'sources') {
				onSources?.((JSON.parse(frame.data) as { sources: ChatSource[] }).sources);
			} else if (frame.event === 'error') {
				throw new Error((JSON.parse(frame.data) as { error: string }).error);
			}

		}
	}
}

export function getSession(sessionId: string): Promise<GetSessionResponse> {
	return request<GetSessionResponse>(`/api/sessions/${encodeURIComponent(sessionId)}`);
}

export async function checkAuth(key: string): Promise<boolean> {
	const res = await fetch(`${baseUrl()}/api/auth/check`, {
		headers: { 'X-Participant-Key': key }
	});
	if (res.status === 401) return false;
	if (!res.ok) {
		const text = await res.text().catch(() => '');
		throw new Error(`API ${res.status} ${res.statusText}: ${text}`);
	}
	return true;
}

export class DuplicateFeedbackError extends Error {}

export async function submitFeedback(payload: FeedbackRequest): Promise<void> {
	const res = await fetch(`${baseUrl()}/api/feedback`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...authHeaders() },
		body: JSON.stringify(payload)
	});
	if (res.ok) return;
	if (res.status === 401) throw unauthorized();
	if (res.status === 409) throw new DuplicateFeedbackError('already submitted');
	const text = await res.text().catch(() => '');
	throw new Error(`API ${res.status} ${res.statusText}: ${text}`);
}
