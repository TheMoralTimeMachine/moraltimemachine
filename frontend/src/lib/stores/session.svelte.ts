import type { ChatMessage, GenerationMode, Reflection, Speed } from '$lib/api';

const STORAGE_KEY = 'mtm_session_v2';

interface VariantState {
	sessionId: string | null;

	featureTitle: string;
	reflections: Reflection[];
	chat: ChatMessage[];
}

interface SessionState {
	description: string;

	mode: GenerationMode;

	compare: boolean;

	variants: Record<Speed, VariantState>;

	view: Speed;

	feedbackSubmitted: boolean;

	feedbackAnswers: {
		likert: Record<string, number | null>;
		open: Record<string, string>;

		demographics: {
			choice: Record<string, string>;
			other: Record<string, string>;
		};
	};
	loading: { reflections: boolean; chat: boolean };

	error: string | null;
}

function emptyVariant(): VariantState {
	return { sessionId: null, featureTitle: '', reflections: [], chat: [] };
}

function emptyState(): SessionState {
	return {
		description: '',
		mode: 'fast',
		compare: false,
		variants: { fast: emptyVariant(), thinking: emptyVariant() },
		view: 'fast',
		feedbackSubmitted: false,
		feedbackAnswers: { likert: {}, open: {}, demographics: { choice: {}, other: {} } },
		loading: { reflections: false, chat: false },
		error: null
	};
}

function loadFromStorage(): SessionState {
	if (typeof window === 'undefined') return emptyState();
	try {
		const raw = sessionStorage.getItem(STORAGE_KEY);
		if (!raw) return emptyState();
		const parsed = JSON.parse(raw) as Partial<SessionState>;
		const base = emptyState();
		return {
			...base,
			...parsed,

			variants: {
				fast: { ...base.variants.fast, ...parsed.variants?.fast },
				thinking: { ...base.variants.thinking, ...parsed.variants?.thinking }
			},

			feedbackAnswers: {
				...base.feedbackAnswers,
				...parsed.feedbackAnswers,
				demographics: {
					...base.feedbackAnswers.demographics,
					...parsed.feedbackAnswers?.demographics
				}
			},

			loading: { reflections: false, chat: false },
			error: null
		};
	} catch {
		return emptyState();
	}
}

function persist(state: SessionState) {
	if (typeof window === 'undefined') return;
	const { loading: _loading, error: _error, ...persistable } = state;
	try {
		sessionStorage.setItem(STORAGE_KEY, JSON.stringify(persistable));
	} catch {

	}
}

function createSessionStore() {

	const state = $state<SessionState>(emptyState());

	function hydrate() {
		if (typeof window === 'undefined') return;
		Object.assign(state, loadFromStorage());
	}

	function save() {
		persist(state);
	}

	function reset() {
		Object.assign(state, emptyState());
		if (typeof window !== 'undefined') {
			sessionStorage.removeItem(STORAGE_KEY);
		}
	}

	return {
		get state() {
			return state;
		},

		get active() {
			return state.variants[state.view];
		},
		hydrate,
		save,
		reset
	};
}

export const session = createSessionStore();
