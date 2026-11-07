import vi, { type MessageKey } from './vi';
import en from './en';

export type Locale = 'vi' | 'en';
const STORAGE_KEY = 'lexora-locale';
const dictionaries: Record<Locale, Record<MessageKey, string>> = { vi, en };

function initial(): Locale {
	const saved = typeof localStorage !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
	if (saved === 'vi' || saved === 'en') return saved;
	return typeof navigator !== 'undefined' && navigator.language.toLowerCase().startsWith('en') ? 'en' : 'vi';
}

const state = $state({ locale: initial() });
if (typeof document !== 'undefined') document.documentElement.lang = state.locale;

export const i18n = {
	get locale(): Locale {
		return state.locale;
	},
	set(locale: Locale) {
		state.locale = locale;
		localStorage.setItem(STORAGE_KEY, locale);
		document.documentElement.lang = locale;
	}
};

/** Translate a key; `{name}` placeholders are filled from params. Reactive: it reads the current locale. */
export function t(key: MessageKey, params?: Record<string, string | number>): string {
	const one = `${key}.one` as MessageKey;
	let text = params?.n === 1 && one in dictionaries[state.locale] ? dictionaries[state.locale][one] : dictionaries[state.locale][key];
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
