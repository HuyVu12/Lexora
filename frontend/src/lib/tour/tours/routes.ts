import { api } from '#lib/api.js';
import type { TourContext } from '../types.js';

/**
 * Route finders shared by the research tours: stay on the open item when the page already shows one,
 * otherwise open the first item of the listing. Null (nothing to open yet) makes the tour explain how to
 * create one instead of failing.
 */
export function firstOf(page: RegExp, listing: string, key: string, path: (id: string) => string) {
	return async (ctx: TourContext): Promise<string | null> => {
		if (page.test(ctx.path)) return ctx.path;
		const data = await api<Record<string, { id: string }[]>>(listing).catch(() => null);
		const first = data?.[key]?.[0];
		return first ? path(first.id) : null;
	};
}

/** The current path when it matches, else null (a page that can only be opened from another one). */
export function onlyHere(page: RegExp) {
	return (ctx: TourContext) => (page.test(ctx.path) ? ctx.path : null);
}
