import { i18n } from './i18n/index.svelte';

export interface Entry {
	term: string;
	definition: string;
	cues?: string;
	example?: string;
	highlight?: string;
}
type Bilingual = Record<string, { vi: Entry; en: Entry }>;

const store = $state<{ data: Bilingual | null }>({ data: null });
let loading: Promise<void> | null = null;

/** The glossary comes from the server (`legal_ai/glossary.py`), the one source shared with the graph viewers. */
export function loadGlossary(): Promise<void> {
	loading ??= fetch('/api/glossary', { credentials: 'same-origin' })
		.then((r) => r.json())
		.then((d: Bilingual) => {
			store.data = d;
		})
		.catch(() => {
			loading = null;
		});
	return loading;
}

export function entry(key: string): Entry | null {
	return store.data?.[key]?.[i18n.locale] ?? null;
}
