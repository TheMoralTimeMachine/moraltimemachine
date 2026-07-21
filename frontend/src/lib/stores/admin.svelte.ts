const STORAGE_KEY = 'mtm_admin_key';

interface AdminState {
	key: string | null;
}

function createAdminStore() {

	const state = $state<AdminState>({ key: null });

	function hydrate() {
		if (typeof window === 'undefined') return;
		try {
			state.key = sessionStorage.getItem(STORAGE_KEY);
		} catch {
			state.key = null;
		}
	}

	function setKey(key: string) {
		state.key = key;
		try {
			sessionStorage.setItem(STORAGE_KEY, key);
		} catch {

		}
	}

	function clear() {
		state.key = null;
		try {
			sessionStorage.removeItem(STORAGE_KEY);
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

export const admin = createAdminStore();
