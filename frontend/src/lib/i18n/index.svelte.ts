import vi, { type MessageKey } from './vi';

export type Locale = 'vi' | 'en';
const STORAGE_KEY = 'lexora-locale';
// Vietnamese ships with the app; English (as large again) loads only when someone switches to it.
const dictionaries: Partial<Record<Locale, Record<MessageKey, string>>> = { vi };
let loadingEn: Promise<void> | null = null;

/** Fetch the English dictionary once. Hovering the language button calls it early, so the switch is instant. */
export function preloadLocale(locale: Locale): Promise<void> {
	if (dictionaries[locale]) return Promise.resolve();
	loadingEn ??= import('./en').then((m) => {
		dictionaries.en = m.default;
	});
	return loadingEn;
}

function initial(): Locale {
	const saved = typeof localStorage !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
	if (saved === 'vi' || saved === 'en') return saved;
	return typeof navigator !== 'undefined' && navigator.language.toLowerCase().startsWith('en') ? 'en' : 'vi';
}

const wanted = initial();
// Until a saved English dictionary has arrived the interface reads Vietnamese; +layout.ts waits for `ready`.
const state = $state({ locale: 'vi' as Locale });
if (typeof document !== 'undefined') document.documentElement.lang = 'vi';
const ready: Promise<void> =
	wanted === 'vi'
		? Promise.resolve()
		: preloadLocale(wanted)
				.then(() => apply(wanted))
				.catch(() => undefined);

function apply(locale: Locale) {
	state.locale = locale;
	document.documentElement.lang = locale;
}

export const i18n = {
	get locale(): Locale {
		return state.locale;
	},
	/** Resolves once the saved locale's dictionary is in place (the first render waits for it). */
	ready,
	async set(locale: Locale) {
		localStorage.setItem(STORAGE_KEY, locale);
		await preloadLocale(locale);
		apply(locale);
	}
};

/** Translate a key; `{name}` placeholders are filled from params. Reactive: it reads the current locale. */
export function t(key: MessageKey, params?: Record<string, string | number>): string {
	const one = `${key}.one` as MessageKey;
	const dict = dictionaries[state.locale] ?? vi;
	let text = params?.n === 1 && one in dict ? dict[one] : dict[key];
	if (params) for (const [name, value] of Object.entries(params)) text = text.replaceAll(`{${name}}`, String(value));
	return text;
}

const tag = () => (state.locale === 'vi' ? 'vi-VN' : 'en-GB');

export function formatDate(iso: string): string {
	return new Date(iso).toLocaleString(tag(), { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export function formatDay(iso: string): string {
	return new Date(iso).toLocaleDateString(tag(), { day: '2-digit', month: '2-digit', year: 'numeric' });
}

/** "upload-…/article-27/clause-1" becomes "Điều 27, khoản 1" in the current locale. */
export function unitLabel(unitId: string): string {
	return unitId
		.split('/')
		.slice(1)
		.map((part) => {
			const [type, ...rest] = part.split('-');
			const key = `unit.${type}` as MessageKey;
			// Unit IDs keep chapter numerals in lower case; statutes write them in capitals (Chương III).
			const label = type === 'chapter' ? rest.join('-').toUpperCase() : rest.join('-');
			return `${key in vi ? t(key) : type} ${label}`;
		})
		.join(', ');
}
