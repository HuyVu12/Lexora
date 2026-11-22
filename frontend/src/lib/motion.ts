/**
 * Lexora motion: one small vocabulary shared by every page.
 *
 * Rules (see the header of app.css for the tokens these mirror):
 * - only transform and opacity move, through the Web Animations API (anime.js `waapi`), so motion stays
 *   on the compositor even while the page is busy loading;
 * - UI motion lasts 120-280 ms, page-level entrances up to ~420 ms; exits are faster than entrances;
 * - nothing waits for an animation before the user can act, and every animation can be interrupted;
 * - `prefers-reduced-motion: reduce` turns every helper into an instant change.
 *
 * anime.js is imported per module (`animejs/waapi`, `animejs/utils`, `animejs/easings/spring`) so only the
 * small WAAPI wrapper, `stagger` and the spring solver reach the bundle, never the JS animation engine.
 */
import { waapi, type WAAPIAnimation } from 'animejs/waapi';
import { stagger } from 'animejs/utils';
import { spring as makeSpring } from 'animejs/easings/spring';
import type { Attachment } from 'svelte/attachments';
import type { TransitionConfig } from 'svelte/transition';

export const DUR = { press: 120, fast: 160, base: 220, slow: 320, page: 420 } as const;
export const EASE = {
	/** Entrances and responses: starts fast, settles softly. */
	out: 'cubic-bezier(0.23, 1, 0.32, 1)',
	/** Things that move from one place on screen to another. */
	inOut: 'cubic-bezier(0.77, 0, 0.175, 1)'
} as const;

/** A crisp spring with a hint of overshoot, for things that pop into place (menus, toasts, the guide button). */
export const springPop = makeSpring({ bounce: 0.18, duration: 300 });
/** A calm spring without overshoot, for larger surfaces. */
export const springSoft = makeSpring({ bounce: 0, duration: 340 });

let reducedQuery: MediaQueryList | null = null;
/** True when the visitor asked the system for less motion. Read at call time, so a live change applies at once. */
export function reducedMotion(): boolean {
	if (typeof window === 'undefined' || !window.matchMedia) return true;
	reducedQuery ??= window.matchMedia('(prefers-reduced-motion: reduce)');
	return reducedQuery.matches;
}

type Targets = Element | Element[] | NodeListOf<Element>;
type Params = Parameters<typeof waapi.animate>[1];

/** anime.js `waapi.animate`, skipped under reduced motion. Inline styles are restored when it ends. */
export function animate(targets: Targets, params: Params): WAAPIAnimation | null {
	const list = targets instanceof Element ? [targets] : [...targets];
	if (!list.length || reducedMotion()) return null;
	const animation = waapi.animate(list as HTMLElement[], params);
	animation.then(() => animation.revert());
	return animation;
}

export interface RevealOptions {
	/** Distance in px the element rises from. */
	y?: number;
	delay?: number;
	duration?: number;
	/** Start scale; 1 keeps the size. */
	scale?: number;
}

/** Attachment: the element fades in and rises a few pixels when it is first rendered. `{@attach reveal()}` */
export function reveal({ y = 8, delay = 0, duration = DUR.slow, scale = 1 }: RevealOptions = {}): Attachment<HTMLElement> {
	return (node) => {
		const animation = animate(node, {
			opacity: [0, 1],
			transform: [`translateY(${y}px) scale(${scale})`, 'none'],
			duration,
			delay,
			ease: EASE.out
		});
		return () => animation?.revert();
	};
}

export interface StaggerOptions extends RevealOptions {
	/** Delay between two neighbours in ms. */
	step?: number;
	/** Children after this many share the last delay, so a long list never takes long to appear. */
	cap?: number;
	/** CSS selector (relative to the container) of the items; direct children by default. */
	items?: string;
	/** Also animate items added later (new chat turns, a fresh list after a filter). */
	live?: boolean;
}

/**
 * Attachment for a list or grid: its items cascade in, `step` ms apart, the first time it renders.
 * With `live`, items added later rise in on their own. `{@attach revealItems({ step: 40 })}`
 */
export function revealItems({ y = 10, delay = 0, duration = DUR.slow, step = 45, cap = 8, items, live = false, scale = 1 }: StaggerOptions = {}): Attachment<HTMLElement> {
	return (node) => {
		const pick = () => (items ? [...node.querySelectorAll<HTMLElement>(items)] : ([...node.children] as HTMLElement[]));
		const running = new Set<WAAPIAnimation>();
		const play = (targets: HTMLElement[], start: number) => {
			const head = targets.slice(0, cap);
			const delays = stagger(step, { start });
			const animation = animate(head, {
				opacity: [0, 1],
				transform: [`translateY(${y}px) scale(${scale})`, 'none'],
				duration,
				delay: delays,
				ease: EASE.out
			});
			if (animation) running.add(animation);
			if (targets.length > cap) {
				const rest = animate(targets.slice(cap), { opacity: [0, 1], duration, delay: start + cap * step, ease: EASE.out });
				if (rest) running.add(rest);
			}
		};
		play(pick(), delay);
		let observer: MutationObserver | undefined;
		if (live) {
			observer = new MutationObserver((records) => {
				const added = records.flatMap((r) => [...r.addedNodes]).filter((n): n is HTMLElement => n instanceof HTMLElement && (!items || n.matches(items)));
				if (added.length) play(added, 0);
			});
			observer.observe(node, { childList: true });
		}
		return () => {
			observer?.disconnect();
			for (const animation of running) animation.revert();
		};
	};
}

/**
 * Attachment: show `value` and count to it from the previous value (from 0 the first time).
 * The element's text is owned by the attachment: render it empty. `<span {@attach countUp(n)}></span>`
 * Numbers use tabular figures in app.css, so counting never shifts the layout.
 */
export function countUp(value: number, { duration = 640, format = (n: number) => n.toLocaleString('vi-VN') } = {}): Attachment<HTMLElement> {
	return (node) => {
		const from = Number(node.dataset.value ?? 0);
		node.dataset.value = String(value);
		if (reducedMotion() || from === value || duration <= 0) {
			node.textContent = format(value);
			return;
		}
		const ease = (t: number) => 1 - Math.pow(1 - t, 3);
		const start = performance.now();
		const span = from === 0 ? duration : Math.min(duration, 360);
		let frame = requestAnimationFrame(function tick(now) {
			const t = Math.min(1, (now - start) / span);
			node.textContent = format(Math.round(from + (value - from) * ease(t)));
			if (t < 1) frame = requestAnimationFrame(tick);
		});
		return () => {
			cancelAnimationFrame(frame);
			node.textContent = format(value);
		};
	};
}

/**
 * Attachment for a highlighted specimen sentence: each `mark` is drawn left to right like a highlighter
 * stroke, one after another. Marks must paint their colour as a background image (see the specimen CSS).
 */
export function highlighterSweep({ delay = 200, step = 110, duration = 420 } = {}): Attachment<HTMLElement> {
	return (node) => {
		const marks = [...node.querySelectorAll<HTMLElement>('mark')];
		const animation = animate(marks, {
			backgroundSize: ['0% 100%', '100% 100%'],
			duration,
			delay: stagger(step, { start: delay }),
			ease: EASE.out
		});
		return () => animation?.revert();
	};
}

/**
 * FLIP for the blocks that follow a change in height (a panel opening or closing above them): records where
 * `elements` are, runs `change`, then slides each one from its old place to its new one with transforms only.
 */
export async function flip(elements: Element[], change: () => void | Promise<void>, { duration = DUR.slow, ease = EASE.out } = {}) {
	if (reducedMotion()) return change();
	const before = elements.map((el) => el.getBoundingClientRect().top);
	await change();
	elements.forEach((el, i) => {
		if (!el.isConnected) return;
		const dy = before[i] - el.getBoundingClientRect().top;
		if (Math.abs(dy) < 1) return;
		animate(el, { transform: [`translateY(${dy}px)`, 'none'], duration, ease });
	});
}

/**
 * Svelte transition for anchored surfaces (menus, popovers, tooltips): a small scale from the anchor's side
 * plus a fade. Pass `origin` to scale from the trigger. Exits use a shorter, plain ease-out.
 */
export function pop(node: Element, { origin = 'top left', y = -4, scale = 0.96, duration }: { origin?: string; y?: number; scale?: number; duration?: number } = {}): TransitionConfig {
	(node as HTMLElement).style.transformOrigin = origin;
	if (reducedMotion()) return { duration: 0 };
	const solved = duration ?? Math.min(springPop.settlingDuration, 520);
	return {
		duration: solved,
		easing: duration ? (t) => 1 - Math.pow(1 - t, 3) : springPop.ease,
		css: (t, u) => `opacity: ${Math.min(1, t * 2)}; transform: translateY(${u * y}px) scale(${scale + (1 - scale) * t});`
	};
}

/** The exit half of `pop`: quicker and without spring, so closing never feels heavier than opening. */
export function popOut(node: Element, { y = -4, scale = 0.97, duration = DUR.fast - 40 }: { y?: number; scale?: number; duration?: number } = {}): TransitionConfig {
	if (reducedMotion()) return { duration: 0 };
	return {
		duration,
		easing: (t) => t * t,
		css: (t, u) => `opacity: ${t}; transform: translateY(${u * y}px) scale(${scale + (1 - scale) * t});`
	};
}

/** Svelte transition: rise a few pixels and fade. For content swapped in place (a card, a status line). */
export function rise(_node: Element, { y = 8, duration = DUR.base, delay = 0 }: { y?: number; duration?: number; delay?: number } = {}): TransitionConfig {
	if (reducedMotion()) return { duration: 0 };
	return {
		duration,
		delay,
		easing: (t) => 1 - Math.pow(1 - t, 3),
		css: (t, u) => `opacity: ${t}; transform: translateY(${u * y}px);`
	};
}
