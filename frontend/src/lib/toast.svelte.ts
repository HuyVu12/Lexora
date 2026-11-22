import type { MessageKey } from './i18n/vi.js';

export type ToastMessage = string | { key: MessageKey; params?: Record<string, string | number> };
export const toast = $state<{ message: ToastMessage | null; error: boolean; id: number }>({ message: null, error: false, id: 0 });
let timer: ReturnType<typeof setTimeout> | undefined;
let remaining = 0;
let startedAt = 0;

function schedule(ms: number) {
	clearTimeout(timer);
	remaining = ms;
	startedAt = Date.now();
	timer = setTimeout(() => (toast.message = null), ms);
}

/** Show a message. Pass a message key (translated at render time) or a server error string. */
export function notify(message: ToastMessage, error = false) {
	toast.message = message;
	toast.error = error;
	toast.id += 1;
	schedule(error ? 9000 : 4500);
}

export function clearToast() {
	clearTimeout(timer);
	toast.message = null;
}

/** Hold the message while the pointer rests on it (or the tab is hidden); `resumeToast` gives back the time left. */
export function pauseToast() {
	if (!toast.message || !timer) return;
	clearTimeout(timer);
	timer = undefined;
	remaining = Math.max(0, remaining - (Date.now() - startedAt));
}

export function resumeToast() {
	if (!toast.message || timer) return;
	schedule(Math.max(1500, remaining));
}

/** Run an async action; a thrown error becomes an error toast. Returns false when it failed. */
export async function act(fn: () => Promise<unknown>): Promise<boolean> {
	try {
		await fn();
		return true;
	} catch (e) {
		notify(e instanceof Error ? e.message : String(e), true);
		return false;
	}
}
