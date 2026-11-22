import type { MessageKey } from '#lib/i18n/vi.js';
import type { Role } from '#lib/types.js';

/**
 * A step-by-step tour: a list of steps, each pointing at one element of the real page that carries
 * `data-tour="<target>"`. Tours never act for the user: a step only explains, waits for the user to do
 * something, or (with `fill`) puts an example into an empty field of a local form without submitting it.
 * tests/test_tours.py checks every `tour.*` key in these files exists in vi.ts and en.ts and every target
 * exists as a `data-tour` attribute in some .svelte file.
 */

/** What a step waits for before Next unlocks. The user can always skip the step instead. */
export type Wait =
	/** The target (or the first input/textarea/select inside it) holds at least `min` characters (default 1). */
	| { kind: 'input'; min?: number }
	/** A click on the target or anything inside it. */
	| { kind: 'click'; within?: string }
	/** A change (radio, checkbox, select) inside the target. */
	| { kind: 'change' }
	/** A non-empty text selection inside an element matching `within` (default: the target). */
	| { kind: 'selection'; within?: string }
	/** An element matching `selector` becomes visible somewhere on the page. */
	| { kind: 'appear'; selector: string }
	/** The path matches `match` (for steps that send the user to another page). */
	| { kind: 'route'; match: RegExp }
	/** Any condition, checked a few times a second. */
	| { kind: 'test'; test: () => boolean };

/** A short, non-destructive demonstration on the step. */
export type Demo =
	/** The example line types itself in the card. */
	| { kind: 'type' }
	/** A highlighter stroke sweeps over the elements matching `selector` (inside the target first, then the page). */
	| { kind: 'sweep'; selector: string };

export interface TourContext {
	role: Role | null;
	path: string;
}

export interface TourStep {
	/** Stable within the tour (used for resuming and in tests). */
	id: string;
	title: MessageKey;
	body: MessageKey;
	/** One line showing how to fill or do it; quoted law must say it is an illustration. */
	example?: MessageKey;
	/** The `data-tour` id of the element to point at. Without it the card sits in the middle of the screen. */
	target?: string;
	/** Among several elements with the same `data-tour` id, prefer the first one matching this selector. */
	prefer?: string;
	/** Which of several matching elements to use when none is preferred: the first (default) or the last (the newest answer). */
	pick?: 'first' | 'last';
	placement?: 'auto' | 'top' | 'bottom' | 'left' | 'right';
	/** Extra room around the target in px (default 6). */
	padding?: number;
	/** Where the step lives. When the current path does not match, the engine navigates to `route`. */
	page?: RegExp;
	/** Path to open for this step, or a function finding one (null: nothing to open, see `missing`). */
	route?: string | ((ctx: TourContext) => string | null | Promise<string | null>);
	roles?: Role[];
	/** False: the step does not apply right now; `missing` is shown instead (or the step is skipped). */
	onlyIf?: (ctx: TourContext) => boolean;
	/** Shown when the target or route is not there: explain how to get there instead of failing. */
	missing?: MessageKey;
	/** Skip silently when the target is absent or hidden (e.g. a link hidden on phones). */
	optional?: boolean;
	wait?: Wait;
	/** Shown under the body until the wait is satisfied. */
	hint?: MessageKey;
	/** Go on by itself once the wait is satisfied (for clicks that open something new). */
	advance?: boolean;
	demo?: Demo;
	/** A "Điền thử" button that writes this example into the target field if it is empty. Never submits. */
	fill?: MessageKey;
}

export interface Tour {
	id: string;
	/** Bump when the steps change enough that a finished tour should be offered again. */
	version: number;
	title: MessageKey;
	summary: MessageKey;
	roles?: Role[];
	/** PageGuide names whose "?" offers this tour. */
	guides: string[];
	/** Where the tour starts when it is opened from elsewhere (the first step's route also works). */
	start?: string;
	/** Offered on the last card. */
	next?: string;
	steps: TourStep[];
}
