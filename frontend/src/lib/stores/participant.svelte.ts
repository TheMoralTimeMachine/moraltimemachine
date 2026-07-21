const STORAGE_KEY = 'mtm_participant_key';

interface ParticipantState {
	key: string | null;
}

function createParticipantStore() {

	const state = $state<ParticipantState>({ key: null });

	function hydrate() {
		if (typeof window === 'undefined') return;
		try {
			state.key = localStorage.getItem(STORAGE_KEY);
		} catch {
			state.key = null;
		}
	}

	function setKey(key: string) {
		state.key = key;
		try {
			localStorage.setItem(STORAGE_KEY, key);
		} catch {

		}
	}

	function clear() {
		state.key = null;
		try {
			localStorage.removeItem(STORAGE_KEY);
		} catch {

		}
	}

	return {
		get key() {
			return state.key;
		},
		hydrate,
		setKey,
		clear
	};
}

export const participant = createParticipantStore();
