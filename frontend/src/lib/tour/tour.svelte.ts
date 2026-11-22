/**
 * The step-by-step tour engine's state: which tour runs, which step is shown, and what each user finished.
 * TourOverlay (mounted once in +layout.svelte) renders it; the "?" beside a page title, the open page guide
 * and the user menu start tours through `startTour`.
 *
 * Persistence: `lexora-tour-<id>` in localStorage holds { v, status, step } (status `done`, `dismissed` or
 * `progress`); a different `version` makes a finished tour new again. The running tour is also kept in
 * sessionStorage, so a reload in the middle of a tour picks it up at the same step.
 */
import { session } from '#lib/session.svelte.js';
import type { Role } from '#lib/types.js';
import { TOURS } from './tours/index.js';
import type { Tour, TourStep } from './types.js';

export type TourStatus = 'new' | 'progress' | 'done' | 'dismissed';

const RUNNING = 'lexora-tour-running';

export const tour = $state({
	/** The running tour, or null. */
	active: null as Tour | null,
	/** Steps of the running tour that apply to the signed-in role. */
	steps: [] as TourStep[],
	index: 0,
	/** Direction of the last move, so a skipped step keeps going the same way. */
	direction: 1 as 1 | -1,
	/** Bumped on every start, so the overlay restarts even when the same tour starts again. */
	run: 0,
	/** Completion marks, refreshed on every change so menus update. */
	marks: {} as Record<string, TourStatus>
});

const storeKey = (id: string) => `lexora-tour-${id}`;

type Saved = { v: number; status: TourStatus; step: number; done?: boolean };

function read(id: string): Saved | null {
	try {
		const raw = localStorage.getItem(storeKey(id));
		return raw ? JSON.parse(raw) : null;
	} catch {
		return null;
	}
}

function write(t: Tour, status: TourStatus, step: number) {
	// A tour finished once stays marked finished, even when it is restarted and closed half way later.
	const before = read(t.id);
	const done = status === 'done' || (!!before?.done && before.v === t.version);
	try {
		localStorage.setItem(storeKey(t.id), JSON.stringify({ v: t.version, status, step, done } satisfies Saved));
	} catch {
		// Private mode: the mark lasts for this page view only.
	}
	tour.marks[t.id] = done ? 'done' : status;
}

/** What the user did with a tour on this machine; an older version counts as new. */
export function tourStatus(id: string): TourStatus {
	if (id in tour.marks) return tour.marks[id];
	const t = TOURS.find((x) => x.id === id);
	const saved = read(id);
	if (!t || !saved || saved.v !== t.version) return 'new';
	return saved.done ? 'done' : saved.status;
}

const allowed = (roles: Role[] | undefined, role: Role | null) => !roles || (!!role && roles.includes(role));

/** Tours the signed-in role can take, in menu order. */
export function toursFor(role: Role | null): Tour[] {
	return TOURS.filter((t) => allowed(t.roles, role));
}

/** The tour offered by a page guide's "?" (by PageGuide name), if the role may take it. */
export function tourForGuide(guide: string, role: Role | null): Tour | null {
	return toursFor(role).find((t) => t.guides.includes(guide)) ?? null;
}

export function startTour(id: string, at = 0) {
	const t = toursFor(session.account?.role ?? null).find((x) => x.id === id);
	if (!t) return;
	tour.active = t;
	tour.steps = t.steps.filter((s) => allowed(s.roles, session.account?.role ?? null));
	tour.index = Math.max(0, Math.min(at, tour.steps.length - 1));
	tour.direction = 1;
	tour.run += 1;
	write(t, 'progress', tour.index);
	remember();
}

function remember() {
	try {
		if (tour.active) sessionStorage.setItem(RUNNING, JSON.stringify({ id: tour.active.id, index: tour.index }));
		else sessionStorage.removeItem(RUNNING);
	} catch {
		// Ignored: resuming after a reload is a convenience.
	}
}

/** After a reload: continue the tour that was running in this tab. */
export function resumeTour() {
	try {
		const raw = sessionStorage.getItem(RUNNING);
		if (!raw || tour.active) return;
		const { id, index } = JSON.parse(raw) as { id: string; index: number };
		startTour(id, index);
	} catch {
		// Nothing to resume.
	}
}

export function goTo(index: number) {
	if (!tour.active) return;
	if (index >= tour.steps.length) return finishTour();
	tour.direction = index < tour.index ? -1 : 1;
	tour.index = Math.max(0, index);
	write(tour.active, 'progress', tour.index);
	remember();
}

export const nextStep = () => goTo(tour.index + 1);
export const previousStep = () => goTo(tour.index - 1);

/** Skip in the direction of the last move (a step that does not apply here). */
export function skipStep() {
	if (tour.direction < 0 && tour.index > 0) goTo(tour.index - 1);
	else goTo(tour.index + 1);
}

export function finishTour() {
	if (tour.active) write(tour.active, 'done', tour.steps.length - 1);
	tour.active = null;
	remember();
}

export function closeTour() {
	if (tour.active) write(tour.active, 'dismissed', tour.index);
	tour.active = null;
	remember();
}
