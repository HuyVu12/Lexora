<script lang="ts">
	import { tick, untrack } from 'svelte';
	import { goto, afterNavigate } from '$app/navigation';
	import Icon from './Icon.svelte';
	import { t } from '#lib/i18n/index.svelte.js';
	import { session } from '#lib/session.svelte.js';
	import { animate, play, reducedMotion, rise, DUR, EASE } from '#lib/motion.js';
	import { tour, nextStep, previousStep, skipStep, finishTour, closeTour, startTour, resumeTour, toursFor } from '#lib/tour/tour.svelte.js';
	import type { TourStep, Wait } from '#lib/tour/types.js';

	// The step-by-step tour: a dimmed page with a rounded window around one real element, and a card next to
	// it. The window glides from one target to the next (transform only); the target stays clickable and
	// reachable by keyboard, everything else is covered by four transparent blockers. Steps that wait for an
	// action watch the page (input, click, change, selection, an element appearing, a route) and unlock Next
	// once it happened; "Skip this step" is always there. The tour never presses Save, Approve or Publish.
	// Under prefers-reduced-motion every move is instant. Mounted once in +layout.svelte.

	type Box = { x: number; y: number; w: number; h: number };
	type Phase = 'shown' | 'missing' | 'blocked' | 'away';

	/** How long to look for a target: long after opening a page (its data may still load), short on the page already open. */
	const SEEK_MS = { afterNavigation: 4500, required: 1500, optional: 400 };
	const PHONE = 640;

	/** What the card shows: it changes only once a step is ready, so quick steps never flash a "looking" state. */
	let view = $state<{ index: number; phase: Phase; key: number }>({ index: 0, phase: 'shown', key: 0 });
	let seeking = $state(false);
	let slow = $state(false);
	let box = $state<Box | null>(null);
	/** The window glides from `glideFrom` to the live box; `glideAt` runs 0 to 1. */
	let glideFrom = $state<Box | null>(null);
	let glideAt = $state(1);
	const easeInOut = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
	/** What is painted. It follows the live box even while gliding, so scrolling mid-move never leaves it behind. */
	const drawn = $derived.by<Box | null>(() => {
		if (!box || !glideFrom || glideAt >= 1) return box;
		const k = easeInOut(glideAt);
		const mix = (a: number, b: number) => a + (b - a) * k;
		return { x: mix(glideFrom.x, box.x), y: mix(glideFrom.y, box.y), w: mix(glideFrom.w, box.w), h: mix(glideFrom.h, box.h) };
	});
	let done = $state(false);
	let card = $state<{ x: number; y: number; dock: boolean; up: boolean; ready: boolean }>({ x: 0, y: 0, dock: false, up: false, ready: false });
	let cardEl = $state<HTMLElement | null>(null);
	let dimEl = $state<SVGSVGElement | null>(null);
	let typed = $state('');
	let sweeps = $state<{ x: number; y: number; w: number; h: number; d: number }[]>([]);
	let sweepRun = $state(0);
	let fillable = $state(false);

	/** The element the window follows (the previous step's, until the next one is found). */
	let tracked: { el: HTMLElement; step: TourStep } | null = null;
	let token = 0;
	let tourNavigating = false;
	let cleanup: (() => void)[] = [];

	const step = $derived<TourStep | null>(tour.active ? (tour.steps[tour.index] ?? null) : null);
	const shown = $derived<TourStep | null>(tour.active ? (tour.steps[view.index] ?? null) : null);
	const phase = $derived(view.phase);
	const total = $derived(tour.steps.length);
	const last = $derived(view.index === total - 1);
	const waiting = $derived(phase === 'shown' && !!shown?.wait && !done && !seeking);
	const nextTour = $derived.by(() => {
		const id = tour.active?.next;
		if (!id) return null;
		return toursFor(session.account?.role ?? null).find((x) => x.id === id) ?? null;
	});
	const backTour = $derived(tour.active ? (toursFor(session.account?.role ?? null).find((x) => x.next === tour.active!.id) ?? null) : null);
	const live = $derived(shown && phase === 'shown' && !seeking ? `${t('tour.ui.counter', { n: view.index + 1, total })}. ${t(shown.title)}. ${t(shown.body)}` : '');

	const selectorFor = (id: string) => `[data-tour="${id}"]`;

	/** An example's value is marked like a phrase on the statute: the quoted parts of a sentence, or all of a bare value. */
	function marked(text: string): { text: string; mark: boolean; quoted?: boolean }[] {
		const parts = text.split(/(“[^”]+”)/).filter(Boolean);
		if (parts.length === 1 && !parts[0].startsWith('“')) return [{ text, mark: true }];
		return parts.map((part) => (part.startsWith('“') ? { text: part.slice(1, -1), mark: true, quoted: true } : { text: part, mark: false }));
	}

	function visible(el: Element) {
		if (!el.isConnected || !el.getClientRects().length) return false;
		const rect = el.getBoundingClientRect();
		return rect.width > 0 && rect.height > 0 && getComputedStyle(el).visibility !== 'hidden';
	}

	/** The step's element: the first visible one carrying its id, preferring one that matches `prefer`. */
	function find(s: TourStep): HTMLElement | null {
		if (!s.target) return null;
		const all = [...document.querySelectorAll<HTMLElement>(selectorFor(s.target))].filter(visible);
		const pool = s.prefer && all.some((el) => el.matches(s.prefer!)) ? all.filter((el) => el.matches(s.prefer!)) : all;
		return (s.pick === 'last' ? pool[pool.length - 1] : pool[0]) ?? null;
	}

	const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
	const frame = () => new Promise((r) => requestAnimationFrame(() => r(null)));
	const viewport = () => ({ w: document.documentElement.clientWidth, h: window.innerHeight });

	/** The target's box plus any parts that belong to it (an open menu marked data-tour-part). */
	function measureBox(el: HTMLElement, s: TourStep): Box {
		const pad = s.padding ?? 6;
		const rects = [el.getBoundingClientRect()];
		if (s.target) for (const part of document.querySelectorAll(`[data-tour-part="${s.target}"]`)) if (visible(part)) rects.push(part.getBoundingClientRect());
		const left = Math.min(...rects.map((r) => r.left));
		const top = Math.min(...rects.map((r) => r.top));
		const right = Math.max(...rects.map((r) => r.right));
		const bottom = Math.max(...rects.map((r) => r.bottom));
		return { x: left - pad, y: top - pad, w: right - left + 2 * pad, h: bottom - top + 2 * pad };
	}

	function same(a: Box | null, b: Box | null) {
		return !!a && !!b && Math.abs(a.x - b.x) < 0.5 && Math.abs(a.y - b.y) < 0.5 && Math.abs(a.w - b.w) < 0.5 && Math.abs(a.h - b.h) < 0.5;
	}

	/** Where the card goes: beside the target on the side with room, shifted to stay on screen; a bottom sheet on phones. */
	function place() {
		if (!cardEl) return;
		const { w: vw, h: vh } = viewport();
		if (vw < PHONE) {
			// A sheet at the bottom; at the top instead when the target sits where the sheet would cover it.
			const ch = cardEl.offsetHeight;
			const up = !!box && box.y + box.h > vh - ch - 8 && box.y > ch + 16;
			if (!card.dock || !card.ready || card.up !== up) card = { x: 0, y: 0, dock: true, up, ready: true };
			return;
		}
		const cw = cardEl.offsetWidth;
		const ch = cardEl.offsetHeight;
		const m = 12;
		const gap = 14;
		const clampX = (x: number) => Math.max(m, Math.min(x, vw - cw - m));
		const clampY = (y: number) => Math.max(m, Math.min(y, vh - ch - m));
		let spot: { x: number; y: number };
		if (!box) {
			spot = { x: (vw - cw) / 2, y: Math.max(m, (vh - ch) / 2 - 20) };
		} else {
			const b = box;
			const options = {
				bottom: { x: clampX(b.x + b.w / 2 - cw / 2), y: b.y + b.h + gap, fits: b.y + b.h + gap + ch <= vh - m },
				top: { x: clampX(b.x + b.w / 2 - cw / 2), y: b.y - gap - ch, fits: b.y - gap - ch >= m },
				right: { x: b.x + b.w + gap, y: clampY(b.y + b.h / 2 - ch / 2), fits: b.x + b.w + gap + cw <= vw - m },
				left: { x: b.x - gap - cw, y: clampY(b.y + b.h / 2 - ch / 2), fits: b.x - gap - cw >= m }
			};
			type Side = keyof typeof options;
			const placement = shown?.placement;
			const preferred = placement && placement !== 'auto' ? [placement as Side] : [];
			const side = ([...preferred, 'bottom', 'right', 'top', 'left'] as Side[]).find((s) => options[s].fits);
			// A target bigger than the screen: the card floats in the lower right corner, over the page.
			spot = side ? options[side] : { x: vw - cw - m - 8, y: vh - ch - m - 8 };
		}
		const x = Math.round(spot.x);
		const y = Math.round(spot.y);
		if (card.x !== x || card.y !== y || card.dock || !card.ready) card = { x, y, dock: false, up: false, ready: true };
	}

	let queued = 0;
	let trailing: ReturnType<typeof setTimeout> | undefined;
	function schedule() {
		// One more look after things settle: transitions run by the Web Animations API end without any event.
		clearTimeout(trailing);
		trailing = setTimeout(schedule2, DUR.page);
		if (queued) return;
		queued = requestAnimationFrame(() => {
			queued = 0;
			measure();
		});
	}

	function schedule2() {
		if (!queued) queued = requestAnimationFrame(() => {
			queued = 0;
			measure();
		});
	}

	function measure() {
		if (tracked) {
			if (!visible(tracked.el)) {
				const again = find(tracked.step);
				if (again) tracked = { el: again, step: tracked.step };
			}
			if (visible(tracked.el)) {
				const next = measureBox(tracked.el, tracked.step);
				if (!same(box, next)) box = next;
			}
		}
		place();
	}

	/** The nearest ancestor (below the page) that scrolls, and whether the element rides on a fixed or sticky one. */
	function context(el: HTMLElement) {
		let pane: HTMLElement | null = null;
		let pinned = false;
		for (let node = el.parentElement; node && node !== document.body; node = node.parentElement) {
			const style = getComputedStyle(node);
			if (!pane && /(auto|scroll)/.test(style.overflowY) && node.scrollHeight > node.clientHeight + 1) pane = node;
			if (style.position === 'fixed' || style.position === 'sticky') pinned = true;
		}
		return { pane, pinned };
	}

	/**
	 * Bring a target into view with room for the card: below or above it when the card cannot sit beside it,
	 * clear of the docked sheet on phones. Resolves once scrolling has settled.
	 */
	async function reveal(el: HTMLElement) {
		const { w: vw, h: vh } = viewport();
		const phone = vw < PHONE;
		const top = 72;
		const bottom = vh - (phone ? Math.max(cardEl?.offsetHeight ?? 0, 240) + 16 : 16);
		const room = bottom - top;
		const { pane, pinned } = context(el);
		if (pane) {
			const inner = el.getBoundingClientRect();
			const frame = pane.getBoundingClientRect();
			if (inner.top < frame.top || inner.bottom > frame.bottom) pane.scrollTop += inner.top - frame.top - Math.max(0, (frame.height - inner.height) / 2);
		}
		const rect = el.getBoundingClientRect();
		const cw = (cardEl?.offsetWidth ?? 360) + 26;
		const ch = (cardEl?.offsetHeight ?? 220) + 14;
		const beside = !phone && (vw - rect.right >= cw || rect.left >= cw);
		const cardFits = phone || beside || rect.top - top >= ch || bottom - rect.bottom >= ch;
		if (rect.top >= top && rect.bottom <= bottom && cardFits) return;
		if (pinned && rect.top >= 0 && rect.bottom <= vh) return;
		const want = !phone && !beside && rect.height + ch <= room ? top + (room - rect.height - ch) / 2 : rect.height <= room ? top + (room - rect.height) / 2 : top;
		const delta = rect.top - want;
		if (Math.abs(delta) < 4) return;
		window.scrollBy({ top: delta, behavior: reducedMotion() ? 'instant' : 'smooth' });
		let before = el.getBoundingClientRect().top;
		for (let i = 0, still = 0; i < 50 && (i < 3 || still < 3); i++) {
			await frame();
			const at = el.getBoundingClientRect().top;
			still = Math.abs(at - before) < 0.5 ? still + 1 : 0;
			before = at;
		}
	}

	// The window is an SVG mask, and Chrome does not repaint a mask whose content runs a compositor animation,
	// so the glide is driven frame by frame (geometry of one rect in a mask: cheap, and never out of date).
	let glideFrame = 0;
	function glide(from: Box | null, to: Box) {
		cancelAnimationFrame(glideFrame);
		const { w: vw, h: vh } = viewport();
		const start = from ?? { x: -40, y: -40, w: vw + 80, h: vh + 80 };
		if (reducedMotion() || same(start, to)) {
			glideAt = 1;
			return;
		}
		glideFrom = start;
		glideAt = 0;
		const began = performance.now();
		const duration = DUR.slow + 60;
		const tickFrame = (now: number) => {
			glideAt = Math.min(1, (now - began) / duration);
			if (glideAt < 1) glideFrame = requestAnimationFrame(tickFrame);
		};
		glideFrame = requestAnimationFrame(tickFrame);
	}

	function moveCard(from: { x: number; y: number } | null) {
		if (!cardEl || reducedMotion() || card.dock || !from) return;
		if (Math.abs(from.x - card.x) < 1 && Math.abs(from.y - card.y) < 1) return;
		play(cardEl, [{ transform: `translate(${from.x}px, ${from.y}px)` }, { transform: `translate(${card.x}px, ${card.y}px)` }], { duration: DUR.slow + 60 });
	}

	function stopWatching() {
		for (const fn of cleanup) fn();
		cleanup = [];
		typed = '';
		sweeps = [];
		fillable = false;
	}

	async function enter(s: TourStep, mine: number) {
		stopWatching();
		// `done` stays as it was until the next step is shown, so a finished action keeps its tick meanwhile.
		seeking = true;
		slow = false;
		const slowTimer = setTimeout(() => mine === token && (slow = true), 450);
		try {
			const ctx = { role: session.account?.role ?? null, path: location.pathname };
			if (s.onlyIf && !s.onlyIf(ctx)) {
				if (s.missing) return await settle('missing', null, mine);
				return skipStep();
			}
			let navigated = false;
			if (s.page && !s.page.test(location.pathname) && s.route) {
				const path = typeof s.route === 'function' ? await s.route(ctx) : s.route;
				if (mine !== token) return;
				if (!path) return await settle('blocked', null, mine);
				tourNavigating = true;
				navigated = true;
				try {
					await goto(path);
				} finally {
					tourNavigating = false;
				}
				if (mine !== token) return;
			}
			if (!s.target) return await settle('shown', null, mine);
			// A page still showing skeletons is loading: give it the long wait too.
			const loading = !!document.querySelector('main [aria-busy="true"]');
			const deadline = performance.now() + (navigated || loading ? SEEK_MS.afterNavigation : s.optional && !s.missing ? SEEK_MS.optional : SEEK_MS.required);
			let el = find(s);
			while (!el && performance.now() < deadline) {
				await sleep(100);
				if (mine !== token) return;
				el = find(s);
			}
			if (!el) {
				if (s.optional && !s.missing) return skipStep();
				return await settle('missing', null, mine);
			}
			await tick();
			await reveal(el);
			if (mine !== token) return;
			await settle('shown', el, mine);
		} finally {
			clearTimeout(slowTimer);
		}
	}

	/** The step is ready: switch the card, move the window and the card, start watching. */
	async function settle(next: Phase, el: HTMLElement | null, mine: number) {
		const s = tour.steps[tour.index];
		const fromBox = drawn;
		const fromCard = card.ready && !card.dock ? { x: card.x, y: card.y } : null;
		tracked = el ? { el, step: s } : null;
		box = el ? measureBox(el, s) : null;
		done = false;
		view = { index: tour.index, phase: next, key: view.key + 1 };
		seeking = false;
		await tick();
		if (mine !== token) return;
		place();
		// The new card position reaches the DOM first; the move then plays from the old one.
		await tick();
		if (box) glide(fromBox, box);
		moveCard(fromCard);
		if (next !== 'shown') {
			cardEl?.focus({ preventScroll: true });
			return;
		}
		watch(s, mine);
		if (s.demo) runDemo(s);
		focusFor(s, el);
	}

	/** Explanation steps take the focus to the card; action steps leave it with (or give it to) the target. */
	function focusFor(s: TourStep, el: HTMLElement | null) {
		const active = document.activeElement;
		const inCard = !!active && !!cardEl?.contains(active);
		if (!s.wait || !el) {
			cardEl?.focus({ preventScroll: true });
			return;
		}
		if (active && active !== document.body && !inCard) return;
		const kind = s.wait.kind;
		const field =
			kind === 'input' || kind === 'change'
				? el.matches('input, textarea, select')
					? el
					: el.querySelector<HTMLElement>('input:not([type=hidden]), textarea, select')
				: kind === 'click'
					? el.matches('button, a, input, select, textarea')
						? el
						: el.querySelector<HTMLElement>('button, a, input, select, textarea')
					: null;
		(field ?? cardEl)?.focus({ preventScroll: true });
	}

	function fieldOf(el: HTMLElement | null | undefined): HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement | null {
		if (!el) return null;
		if (el.matches('input, textarea, select')) return el as HTMLInputElement;
		return el.querySelector('input:not([type=radio]):not([type=checkbox]):not([type=file]):not([type=hidden]), textarea, select');
	}

	function satisfied(w: Wait, s: TourStep): boolean {
		switch (w.kind) {
			case 'input': {
				const field = fieldOf(tracked?.el ?? find(s));
				return !!field && field.value.trim().length >= (w.min ?? 1);
			}
			case 'selection': {
				const sel = getSelection();
				if (!sel || sel.isCollapsed || !sel.rangeCount || !sel.toString().trim()) return false;
				const node = sel.getRangeAt(0).commonAncestorContainer;
				const host = node.nodeType === Node.ELEMENT_NODE ? (node as Element) : node.parentElement;
				return !!host?.closest(w.within ?? selectorFor(s.target ?? ''));
			}
			case 'appear':
				return [...document.querySelectorAll(w.selector)].some(visible);
			case 'route':
				return w.match.test(location.pathname);
			case 'test':
				return w.test();
			default:
				return false;
		}
	}

	function emptyField() {
		const field = fieldOf(tracked?.el);
		return !!field && !(field instanceof HTMLSelectElement) && !field.value.trim();
	}

	function watch(s: TourStep, mine: number) {
		fillable = !!s.fill && emptyField();
		const w = s.wait;
		if (!w && !s.fill) return;
		const succeed = () => {
			if (done || mine !== token) return;
			done = true;
			fillable = false;
			if (s.advance) setTimeout(() => mine === token && nextStep(), reducedMotion() ? 0 : 450);
		};
		const check = () => {
			if (s.fill) fillable = !done && emptyField();
			if (w && w.kind !== 'click' && w.kind !== 'change' && satisfied(w, s)) succeed();
		};
		const onClick = (event: Event) => {
			if (w?.kind !== 'click' || cardEl?.contains(event.target as Node)) return;
			const hit = (event.target as Element | null)?.closest?.(w.within ?? selectorFor(s.target ?? ''));
			if (hit) succeed();
		};
		const onChange = (event: Event) => {
			if (w?.kind === 'change' && tracked?.el.contains(event.target as Node)) succeed();
			check();
		};
		document.addEventListener('click', onClick, true);
		document.addEventListener('change', onChange, true);
		document.addEventListener('input', onChange, true);
		document.addEventListener('selectionchange', check);
		const poll = setInterval(check, 250);
		check();
		cleanup.push(() => {
			document.removeEventListener('click', onClick, true);
			document.removeEventListener('change', onChange, true);
			document.removeEventListener('input', onChange, true);
			document.removeEventListener('selectionchange', check);
			clearInterval(poll);
		});
	}

	function runDemo(s: TourStep) {
		const demo = s.demo;
		if (!demo) return;
		if (demo.kind === 'type' && s.example) {
			const text = t(s.example);
			if (reducedMotion()) {
				typed = text;
				return;
			}
			typed = '';
			let i = 0;
			const timer = setInterval(() => {
				i += 1;
				typed = text.slice(0, i);
				if (i >= text.length) clearInterval(timer);
			}, 32);
			cleanup.push(() => clearInterval(timer));
		}
		if (demo.kind === 'sweep') sweep(demo.selector);
	}

	/** A highlighter stroke drawn over the words to look at, in the tour's own layer: the page is not touched. */
	function sweep(selector: string) {
		const scope = tracked?.el ?? document.body;
		let marks: Element[] = [];
		for (const part of selector.split(',')) {
			marks = [...scope.querySelectorAll(part.trim())].filter(visible);
			if (marks.length) break;
		}
		const rects = marks
			.slice(0, 6)
			.flatMap((m) => [...m.getClientRects()])
			.slice(0, 10);
		sweeps = rects.map((r, i) => ({ x: r.left - 2, y: r.top + 1, w: r.width + 4, h: r.height - 2, d: i * 90 }));
		sweepRun += 1;
		const clear = setTimeout(() => (sweeps = []), 2000 + rects.length * 90);
		const drop = () => (sweeps = []);
		window.addEventListener('scroll', drop, { once: true, capture: true });
		cleanup.push(() => {
			clearTimeout(clear);
			window.removeEventListener('scroll', drop, true);
		});
	}

	/** "Điền thử": writes the example into the empty field of this local form; nothing is submitted or saved. */
	function fill() {
		const field = fieldOf(tracked?.el);
		if (!shown?.fill || !field || field.value.trim() || field instanceof HTMLSelectElement) return;
		const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(field), 'value')?.set;
		setter?.call(field, t(shown.fill));
		field.dispatchEvent(new Event('input', { bubbles: true }));
		field.focus({ preventScroll: true });
		fillable = false;
	}

	// A new step, a new start or a closed tour.
	$effect(() => {
		const s = step;
		void tour.run;
		const mine = ++token;
		if (!s) {
			stopWatching();
			tracked = null;
			box = null;
			card.ready = false;
			return;
		}
		// The step's own work (reading the page, writing the card's state) must not become this effect's dependencies.
		untrack(() => enter(s, mine));
	});

	// While a tour runs, the window follows its element through scrolling, resizing and layout changes.
	$effect(() => {
		if (!tour.active) return;
		const resize = new ResizeObserver(schedule);
		resize.observe(document.body);
		const mutations = new MutationObserver((records) => {
			if (records.some((r) => !cardEl?.contains(r.target))) schedule();
		});
		mutations.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'style', 'open', 'hidden', 'aria-expanded'] });
		window.addEventListener('scroll', schedule, true);
		window.addEventListener('resize', schedule);
		// A menu or panel that scales or slides into place changes no attribute when it lands: measure again then.
		document.addEventListener('transitionend', schedule, true);
		document.addEventListener('animationend', schedule, true);
		return () => {
			document.removeEventListener('transitionend', schedule, true);
			document.removeEventListener('animationend', schedule, true);
			resize.disconnect();
			mutations.disconnect();
			window.removeEventListener('scroll', schedule, true);
			window.removeEventListener('resize', schedule);
			cancelAnimationFrame(queued);
			cancelAnimationFrame(glideFrame);
			clearTimeout(trailing);
			queued = 0;
		};
	});

	$effect(() => {
		if (!session.checked || !session.account) return;
		untrack(resumeTour);
	});

	let restore: HTMLElement | null = null;
	$effect(() => {
		if (tour.active) {
			restore ??= document.activeElement instanceof HTMLElement ? document.activeElement : null;
			return;
		}
		if (restore?.isConnected) restore.focus({ preventScroll: true });
		restore = null;
	});

	$effect(() => {
		if (!dimEl || reducedMotion()) return;
		animate(dimEl, { opacity: [0, 1], duration: DUR.slow, ease: EASE.out });
	});

	// Leaving the step's page by hand pauses the tour instead of dragging the user back.
	afterNavigate(() => {
		const s = shown;
		if (!s || !tour.active || tourNavigating || seeking) return;
		if (view.phase === 'shown' && s.page && !s.page.test(location.pathname)) {
			stopWatching();
			tracked = null;
			box = null;
			view = { index: view.index, phase: 'away', key: view.key + 1 };
			tick().then(place);
		}
	});

	const canNext = $derived(!seeking && phase !== 'blocked' && phase !== 'away' && (!shown?.wait || done || phase !== 'shown'));

	function next() {
		if (!canNext) return;
		if (last) finishTour();
		else nextStep();
	}

	function resume() {
		if (step) enter(step, ++token);
	}

	function onKey(event: KeyboardEvent) {
		if (!tour.active || document.querySelector('dialog[open]')) return;
		const active = document.activeElement as HTMLElement | null;
		const typing = !!active && (active.matches('input, textarea, select') || active.isContentEditable);
		if (event.key === 'Escape') {
			event.preventDefault();
			closeTour();
		} else if (typing) {
			return;
		} else if (event.key === 'ArrowRight') {
			event.preventDefault();
			next();
		} else if (event.key === 'ArrowLeft' && tour.index > 0) {
			event.preventDefault();
			previousStep();
		} else if (event.key === 'Enter' && (!active || active === document.body || active === cardEl)) {
			event.preventDefault();
			next();
		}
	}

	/** A click outside the window: the card gives a small shake instead of the page reacting. */
	function nudge() {
		const inner = cardEl?.querySelector('.inner');
		if (inner && !reducedMotion()) animate(inner, { transform: ['translateX(0)', 'translateX(-5px)', 'translateX(4px)', 'translateX(0)'], duration: 260, ease: EASE.out });
	}

	const keep = (event: MouseEvent) => event.preventDefault();
	const blockers = $derived.by(() => {
		if (!box) return [{ left: '0', top: '0', width: '100%', height: '100%' }];
		const b = box;
		const px = (n: number) => `${Math.max(0, Math.round(n))}px`;
		return [
			{ left: '0', top: '0', width: '100%', height: px(b.y) },
			{ left: '0', top: px(b.y + b.h), width: '100%', height: `calc(100% - ${px(b.y + b.h)})` },
			{ left: '0', top: px(b.y), width: px(b.x), height: px(b.h) },
			{ left: px(b.x + b.w), top: px(b.y), width: `calc(100% - ${px(b.x + b.w)})`, height: px(b.h) }
		];
	});
</script>

<svelte:window onkeydown={onKey} />

{#if tour.active && shown && session.account}
	<div class="tour" class:waiting>
		<svg class="dim" bind:this={dimEl} aria-hidden="true">
			<defs>
				<mask id="tour-hole" maskUnits="userSpaceOnUse" x="0" y="0" width="100%" height="100%">
					<rect width="100%" height="100%" fill="white" />
					{#if drawn}
						<rect class="cut" width={drawn.w} height={drawn.h} rx="10" fill="black" style:transform="translate({drawn.x}px, {drawn.y}px)" />
					{/if}
				</mask>
			</defs>
			<rect class="shade" width="100%" height="100%" mask="url(#tour-hole)" />
			{#if drawn}
				<rect class="ring" width={drawn.w} height={drawn.h} rx="10" style:transform="translate({drawn.x}px, {drawn.y}px)" />
			{/if}
		</svg>
		{#each blockers as b, i (i)}
			<div class="block" style:left={b.left} style:top={b.top} style:width={b.width} style:height={b.height} onpointerdown={nudge} aria-hidden="true"></div>
		{/each}
		{#each sweeps as s, i (`${sweepRun}-${i}`)}
			<span class="sweep" style:left="{s.x}px" style:top="{s.y}px" style:width="{s.w}px" style:height="{s.h}px" style:--d="{s.d}ms" aria-hidden="true"></span>
		{/each}

		<div
			class="card"
			data-step={shown.id}
			data-target={phase === 'shown' ? shown.target : undefined}
			data-phase={seeking ? 'seeking' : phase}
			class:dock={card.dock}
			class:up={card.dock && card.up}
			class:ready={card.ready}
			bind:this={cardEl}
			role="dialog"
			aria-modal="false"
			aria-labelledby="tour-title"
			aria-describedby="tour-body"
			tabindex="-1"
			style:transform={card.dock ? undefined : `translate(${card.x}px, ${card.y}px)`}
		>
			<div class="inner">
				<div class="bar" aria-hidden="true"><i style:transform="scaleX({(view.index + 1) / Math.max(1, total)})"></i></div>
				<header>
					<span class="counter"
						>{t('tour.ui.counter', { n: view.index + 1, total })}<span class="sep" aria-hidden="true">·</span><span class="name">{t(tour.active.title)}</span></span
					>
					<button type="button" class="x" onmousedown={keep} onclick={closeTour} aria-label={t('tour.ui.close')} title={t('tour.ui.closeHint')}><Icon name="x" size={16} /></button>
				</header>
				{#key view.key}
					<div class="content" in:rise={{ y: 4, duration: DUR.base }}>
						{#if phase === 'blocked' || phase === 'missing'}
							<h2 id="tour-title" class="title">{t(shown.title)}</h2>
							<p id="tour-body" class="body">{t(shown.missing ?? 'tour.ui.notFound')}</p>
						{:else if phase === 'away'}
							<h2 id="tour-title" class="title">{t('tour.ui.awayTitle')}</h2>
							<p id="tour-body" class="body">{t('tour.ui.away')}</p>
						{:else}
							<h2 id="tour-title" class="title">{t(shown.title)}</h2>
							<p id="tour-body" class="body">{t(shown.body)}</p>
							{#if shown.example}
								<div class="example">
									<div class="ex-head">
										<span class="label">{t('tour.ui.example')}</span>
										{#if fillable && phase === 'shown'}
											<button type="button" class="btn small fill" title={t('tour.ui.fillHint')} onmousedown={keep} onclick={fill}><Icon name="edit" size={14} />{t('tour.ui.fill')}</button>
										{/if}
									</div>
									{#if shown.demo?.kind === 'type'}
										<p lang="vi"><span aria-hidden="true">{#if typed}<mark>{typed}</mark>{/if}<span class="caret" class:off={typed.length >= t(shown.example).length}></span></span><span class="visually-hidden">{t(shown.example)}</span></p>
									{:else}
										<p lang="vi">
											{#each marked(t(shown.example)) as part, i (i)}{#if part.mark}{part.quoted ? '“' : ''}<mark>{part.text}</mark>{part.quoted ? '”' : ''}{:else}{part.text}{/if}{/each}
										</p>
									{/if}
								</div>
							{/if}
							{#if shown.wait}
								<p class="hint" class:ok={done} role="status">
									{#if done}<Icon name="check" size={16} />{t('tour.ui.done')}{:else}<span class="dot" aria-hidden="true"></span>{t(shown.hint ?? 'tour.ui.waitDefault')}{/if}
								</p>
							{/if}
						{/if}
					</div>
				{/key}
				{#if seeking && slow}<p class="seeking small muted" role="status">{t('tour.ui.seeking')}</p>{/if}
				<footer>
					{#if phase === 'blocked'}
						{#if backTour}<button type="button" class="btn small" onmousedown={keep} onclick={() => startTour(backTour.id)}>{t('tour.ui.open', { name: t(backTour.title) })}</button>{/if}
						<button type="button" class="btn primary small" onmousedown={keep} onclick={closeTour}>{t('tour.ui.close')}</button>
					{:else if phase === 'away'}
						<button type="button" class="btn quiet small" onmousedown={keep} onclick={closeTour}>{t('tour.ui.close')}</button>
						<button type="button" class="btn primary small" onmousedown={keep} onclick={resume}>{t('tour.ui.return')}</button>
					{:else}
						<div class="left">
							{#if view.index > 0}<button type="button" class="btn quiet small" onmousedown={keep} onclick={previousStep}><Icon name="back" size={16} />{t('tour.ui.back')}</button>{/if}
							{#if shown.demo?.kind === 'sweep' && phase === 'shown' && box}
								<button type="button" class="btn quiet small" onmousedown={keep} onclick={() => shown?.demo?.kind === 'sweep' && sweep(shown.demo.selector)}>{t('tour.ui.replay')}</button>
							{/if}
						</div>
						<div class="right">
							{#if waiting || phase === 'missing'}
								<button type="button" class="btn quiet small skip" onmousedown={keep} onclick={nextStep}>{t('tour.ui.skip')}</button>
							{/if}
							{#if last && nextTour}
								<button type="button" class="btn small" onmousedown={keep} onclick={() => { finishTour(); startTour(nextTour.id); }}>{t('tour.ui.open', { name: t(nextTour.title) })}</button>
							{/if}
							{#if !waiting && phase !== 'missing'}
								<button type="button" class="btn primary small" onmousedown={keep} onclick={next} disabled={!canNext}>
									{last ? t('tour.ui.finish') : t('tour.ui.next')}{#if !last}<Icon name="arrow" size={16} />{/if}
								</button>
							{/if}
						</div>
					{/if}
				</footer>
			</div>
		</div>
		<p class="visually-hidden" aria-live="polite">{live}</p>
	</div>
{/if}

<style>
	.tour {
		position: fixed;
		inset: 0;
		z-index: 80;
		pointer-events: none;
	}
	.dim {
		position: fixed;
		inset: 0;
		width: 100%;
		height: 100%;
		overflow: visible;
	}
	.shade {
		fill: rgb(20 22 24 / 0.52);
	}
	.cut,
	.ring {
		transform-origin: 0 0;
		transform-box: view-box;
	}
	.ring {
		fill: none;
		stroke: var(--hl-actor);
		stroke-width: 2.5;
		vector-effect: non-scaling-stroke;
		filter: drop-shadow(0 0 6px color-mix(in srgb, var(--hl-actor) 45%, transparent));
	}
	/* An action step: the window's edge breathes softly until the user acts (opacity only). */
	.waiting .ring {
		animation: breathe 1.6s ease-in-out infinite;
	}
	@keyframes breathe {
		50% {
			stroke-opacity: 0.45;
		}
	}
	.block {
		position: fixed;
		pointer-events: auto;
	}
	.sweep {
		position: fixed;
		border-radius: 3px;
		background: var(--hl-actor);
		opacity: 0.6;
		mix-blend-mode: multiply;
		transform-origin: 0 50%;
		pointer-events: none;
		animation:
			stroke 420ms var(--ease-out) calc(var(--d) + 150ms) both,
			stroke-out var(--dur-slow) ease calc(var(--d) + 1500ms) forwards;
	}
	@keyframes stroke {
		from {
			transform: scaleX(0);
		}
	}
	@keyframes stroke-out {
		to {
			opacity: 0;
		}
	}
	.seeking {
		margin-top: -2px;
	}
	.card {
		position: fixed;
		top: 0;
		left: 0;
		width: 360px;
		max-width: calc(100vw - 24px);
		pointer-events: auto;
		visibility: hidden;
		outline: none;
	}
	.card.ready {
		visibility: visible;
	}
	.inner {
		position: relative;
		overflow: hidden;
		display: grid;
		gap: 10px;
		padding: 16px 18px 14px;
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: 10px;
		box-shadow: var(--shadow-pop);
	}
	.card:focus-visible .inner {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	.bar {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 3px;
		background: var(--desk);
	}
	.bar i {
		position: absolute;
		inset: 0;
		background: var(--flag);
		transform-origin: 0 50%;
		transition: transform var(--dur-slow) var(--ease-out);
	}
	header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		margin-top: 2px;
	}
	.counter {
		display: flex;
		align-items: baseline;
		min-width: 0;
		font-size: 12.5px;
		font-weight: 600;
		color: var(--flag);
		letter-spacing: 0.01em;
	}
	.counter .sep {
		margin: 0 6px;
		color: var(--rule-strong);
	}
	.counter .name {
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
		color: var(--muted);
		font-weight: 500;
	}
	.x {
		flex: none;
		display: grid;
		place-items: center;
		width: 28px;
		height: 28px;
		margin: -6px -8px -6px 0;
		border: 0;
		border-radius: var(--r-control);
		background: none;
		color: var(--muted);
		cursor: pointer;
	}
	.x:hover {
		background: var(--desk);
		color: var(--ink);
	}
	.content {
		display: grid;
		gap: 8px;
	}
	.title {
		font: 600 18px/1.3 var(--serif);
		color: var(--ink);
		text-wrap: balance;
	}
	.body {
		font-size: 14.5px;
		line-height: 1.55;
		color: var(--ink-2);
		text-wrap: pretty;
	}
	.example {
		display: grid;
		gap: 3px;
		padding: 8px 12px 9px;
		border: 1px solid var(--rule);
		border-radius: var(--r-control);
		background: var(--desk);
		background: color-mix(in srgb, var(--desk) 45%, var(--paper));
	}
	.ex-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		min-height: 20px;
	}
	.example .label {
		font-size: 12px;
	}
	.fill {
		min-height: 26px;
		margin: -3px -6px -3px 0;
		padding: 2px 8px;
		gap: 5px;
		font-size: 12.5px;
		background: var(--paper);
	}
	/* The example value is marked like a phrase on the statute: a highlighter stroke, ink stays ink. */
	.example p {
		font: 15px/1.6 var(--serif);
		color: var(--ink);
		min-height: 1.6em;
	}
	.example mark {
		padding: 1px 2px;
		border-radius: 2px;
		background: var(--hl-actor);
		color: var(--ink);
		-webkit-box-decoration-break: clone;
		box-decoration-break: clone;
	}
	.caret {
		display: inline-block;
		width: 1.5px;
		height: 1.05em;
		margin-left: 1px;
		vertical-align: -0.15em;
		background: var(--ink);
		animation: blink 1s steps(1) infinite;
	}
	.caret.off {
		display: none;
	}
	@keyframes blink {
		50% {
			opacity: 0;
		}
	}
	.hint {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 7px 10px;
		border-radius: 6px;
		background: color-mix(in srgb, var(--flag) 8%, var(--paper));
		color: var(--flag);
		font-size: 13.5px;
		font-weight: 500;
	}
	.hint.ok {
		background: var(--approve-soft);
		color: var(--approve);
	}
	.dot {
		flex: none;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--flag);
		animation: breathe-dot 1.4s ease-in-out infinite;
	}
	@keyframes breathe-dot {
		50% {
			opacity: 0.35;
		}
	}
	footer {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		flex-wrap: wrap;
		margin-top: 2px;
	}
	footer:has(> .btn:only-child),
	footer:has(> .btn + .btn) {
		justify-content: flex-end;
	}
	.left,
	.right {
		display: flex;
		align-items: center;
		gap: 6px;
		flex-wrap: wrap;
	}
	.right {
		margin-left: auto;
	}
	.left .btn.quiet:first-child {
		margin-left: -8px;
	}
	.skip {
		color: var(--muted);
	}
	/* Phones: the card docks to the bottom as a sheet, so the target above stays visible. */
	.card.dock {
		top: auto;
		bottom: 0;
		width: 100%;
		max-width: none;
	}
	.card.dock .inner {
		border-radius: 14px 14px 0 0;
		border-width: 1px 0 0;
		padding: 16px 16px calc(14px + env(safe-area-inset-bottom));
		max-height: 52vh;
		overflow-y: auto;
		animation: sheet-in var(--dur-slow) var(--ease-drawer) both;
	}
	.card.dock.up {
		top: 0;
		bottom: auto;
	}
	.card.dock.up .inner {
		border-radius: 0 0 14px 14px;
		border-width: 0 0 1px;
		padding: calc(16px + env(safe-area-inset-top)) 16px 14px;
		animation-name: sheet-down;
	}
	@keyframes sheet-down {
		from {
			transform: translateY(-24px);
			opacity: 0;
		}
	}
	@keyframes sheet-in {
		from {
			transform: translateY(24px);
			opacity: 0;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.waiting .ring,
		.dot,
		.caret {
			animation: none;
		}
		.sweep {
			animation: stroke-out var(--dur-slow) ease calc(var(--d) + 1500ms) forwards;
		}
		.card.dock .inner {
			animation: none;
		}
		.bar i {
			transition: none;
		}
	}
</style>
