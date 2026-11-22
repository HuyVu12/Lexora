import { goto } from '$app/navigation';
import { untrack } from 'svelte';
import { session } from './session.svelte';
import { activity } from './activity.svelte';

const token = document.querySelector<HTMLMetaElement>('meta[name="lexora-token"]')?.content ?? '';

export class ApiError extends Error {
	constructor(
		message: string,
		readonly status: number,
		readonly code?: string
	) {
		super(message);
	}
}

/** Same-origin JSON call. A POST carries the per-process token; a 401 ends the session and opens the login page. */
export async function api<T>(path: string, body?: unknown): Promise<T> {
	const init: RequestInit =
		body === undefined
			? { credentials: 'same-origin' }
			: {
					method: 'POST',
					credentials: 'same-origin',
					headers: { 'Content-Type': 'application/json', 'X-Lexora-Token': token },
					body: JSON.stringify(body)
				};
	// Untracked: an effect that calls api() must not come to depend on the request counter.
	untrack(() => (activity.requests += 1));
	let response: Response;
	let value: { error?: string; code?: string } = {};
	try {
		response = await fetch(path, init);
		try {
			value = await response.json();
		} catch {
			// A non-JSON body leaves the status code as the only signal.
		}
	} finally {
		untrack(() => (activity.requests -= 1));
	}
	if (response.status === 401 && !path.startsWith('/api/auth/')) {
		session.account = null;
		await goto(`/login?expired=1&next=${encodeURIComponent(location.pathname + location.search)}`);
	}
	if (!response.ok) throw new ApiError(value.error ?? `HTTP ${response.status}`, response.status, value.code);
	return value as T;
}
