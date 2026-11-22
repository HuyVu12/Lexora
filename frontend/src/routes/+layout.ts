import { i18n } from '#lib/i18n/index.svelte.js';

// A client-only app: FastAPI serves the shell, every page renders in the browser.
export const ssr = false;
export const prerender = false;

// The first render waits for a saved English dictionary, so an English reader never sees Vietnamese flash by.
export const load = () => i18n.ready;
