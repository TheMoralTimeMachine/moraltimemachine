const STORAGE_KEY = 'mtm_prolific_pid';
const PARAM = 'PROLIFIC_PID';

function createProlificStore() {

	const state = $state<{ pid: string }>({ pid: '' });

	function hydrate() {
		if (typeof window === 'undefined') return;

		let fromUrl = '';
		try {
			fromUrl = new URLSearchParams(window.location.search).get(PARAM)?.trim() ?? '';
		} catch {
			fromUrl = '';
		}
		if (fromUrl) {
			state.pid = fromUrl;
			try {
				localStorage.setItem(STORAGE_KEY, fromUrl);
			} catch {

			}
			return;
		}
		try {
			state.pid = localStorage.getItem(STORAGE_KEY) ?? '';
		} catch {
			state.pid = '';
		}
	}

	return {
		get pid() {
			return state.pid;
		},
		hydrate
	};
}

export const prolific = createProlificStore();
