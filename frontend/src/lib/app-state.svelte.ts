import { api } from './api';
import { session } from './session.svelte';
import type { AppState } from './types';

// One shared copy of /api/state for the overview, chat and import pages: a page shows the last copy at once
// and refreshes it in the background (stale while revalidate), and simultaneous callers share one request.
// The copy belongs to one account; signing in as someone else never shows the previous account's data.
const cache = $state<{ value: AppState | null; owner: string | null }>({ value: null, owner: null });
let inflight: Promise<AppState> | null = null;

const owner = () => session.account?.username ?? null;

/** The last loaded state for the signed-in account, or null. */
export function cachedAppState(): AppState | null {
	return cache.owner === owner() ? cache.value : null;
}

/** Load /api/state; concurrent calls share one request. The result also refreshes the cached copy. */
export function loadAppState(): Promise<AppState> {
	const who = owner();
	inflight ??= api<AppState>('/api/state')
		.then((value) => {
			cache.value = value;
			cache.owner = who;
			return value;
		})
		.finally(() => {
			inflight = null;
		});
	return inflight;
}

/** Forget the cached copy (after sign-out). */
export function clearAppState() {
	cache.value = null;
	cache.owner = null;
}
