<script lang="ts">
	import { onMount } from 'svelte';
	import { entry, loadGlossary, type Entry } from '#lib/glossary.svelte.js';
	import { i18n } from '#lib/i18n/index.svelte.js';

	// One floating explanation for every element with data-term, opened by pointer, focus or tap,
	// closed by leaving, blur, Escape or scrolling. Text is rendered as text, never as HTML.
	let anchor = $state<HTMLElement | null>(null);
	let key = $state<string | null>(null);
	let tip = $state<HTMLDivElement | null>(null);
	let pos = $state({ left: 0, top: 0, above: false });
	let hideTimer: ReturnType<typeof setTimeout> | undefined;

	const current: Entry | null = $derived(key ? entry(key) : null);
	const example = $derived.by(() => {
		if (!current?.example) return null;
		const at = current.highlight ? current.example.indexOf(current.highlight) : -1;
		return at < 0
			? { before: current.example, mark: '', after: '' }
			: { before: current.example.slice(0, at), mark: current.highlight!, after: current.example.slice(at + current.highlight!.length) };
	});

	function termOf(node: EventTarget | null): HTMLElement | null {
		return node instanceof Element ? node.closest<HTMLElement>('[data-term]') : null;
	}

	function show(target: HTMLElement) {
		clearTimeout(hideTimer);
		if (!entry(target.dataset.term ?? '')) return;
		if (anchor && anchor !== target) anchor.removeAttribute('aria-describedby');
		anchor = target;
		key = target.dataset.term ?? null;
		target.setAttribute('aria-describedby', 'glossary-tip');
		requestAnimationFrame(place);
	}

	function hide(now: boolean) {
		clearTimeout(hideTimer);
		const go = () => {
			anchor?.removeAttribute('aria-describedby');
			anchor = null;
			key = null;
		};
		if (now) go();
		else hideTimer = setTimeout(go, 140);
	}

	function place() {
		if (!anchor || !tip) return;
		const r = anchor.getClientRects()[0] ?? anchor.getBoundingClientRect();
		const w = tip.offsetWidth;
		const h = tip.offsetHeight;
		const left = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), innerWidth - w - 8);
		let top = r.bottom + 8;
		let above = false;
		if (top + h > innerHeight - 8 && r.top - 8 - h > 8) {
			top = r.top - 8 - h;
			above = true;
		}
		pos = { left: Math.round(left), top: Math.round(top), above };
	}

	onMount(() => {
		loadGlossary();
		const over = (e: PointerEvent) => {
			if (tip?.contains(e.target as Node)) return clearTimeout(hideTimer);
			const target = termOf(e.target);
			if (target) show(target);
			else if (anchor) hide(false);
		};
		const focusIn = (e: FocusEvent) => {
			const target = termOf(e.target);
			if (target) show(target);
			else if (anchor) hide(true);
		};
		const focusOut = (e: FocusEvent) => termOf(e.target) === anchor && hide(false);
		const key = (e: KeyboardEvent) => e.key === 'Escape' && anchor && hide(true);
		const scroll = () => anchor && hide(true);
		document.addEventListener('pointerover', over);
		document.addEventListener('focusin', focusIn);
		document.addEventListener('focusout', focusOut);
		document.addEventListener('keydown', key);
		window.addEventListener('scroll', scroll, true);
		window.addEventListener('resize', scroll);
		return () => {
			document.removeEventListener('pointerover', over);
			document.removeEventListener('focusin', focusIn);
			document.removeEventListener('focusout', focusOut);
			document.removeEventListener('keydown', key);
			window.removeEventListener('scroll', scroll, true);
			window.removeEventListener('resize', scroll);
		};
	});
</script>

{#if current}
	<div
		id="glossary-tip"
		role="tooltip"
		bind:this={tip}
		class:above={pos.above}
		style:left="{pos.left}px"
		style:top="{pos.top}px"
	>
		<p class="term">{current.term}</p>
		<p class="def">{current.definition}</p>
		{#if current.cues}
			<p class="cues"><span>{i18n.locale === 'vi' ? 'Dấu hiệu nhận biết' : 'Cue words'}</span>{current.cues}</p>
		{/if}
		{#if example}
			<div class="example">
				<span>{i18n.locale === 'vi' ? 'Ví dụ minh họa' : 'Illustrative example'}</span>
				<p lang="vi">{example.before}<mark>{example.mark}</mark>{example.after}</p>
			</div>
		{/if}
	</div>
{/if}

<style>
	#glossary-tip {
		position: fixed;
		z-index: 100;
		width: min(340px, calc(100vw - 16px));
		padding: 14px 16px 15px;
		background: var(--graphite);
		color: #eef0f2;
		border-radius: 10px;
		box-shadow: var(--shadow-pop);
		font-size: 13.5px;
		line-height: 1.55;
		animation: rise 0.18s var(--ease-out);
	}
	#glossary-tip.above {
		animation-name: drop;
	}
	.term {
		font: 600 15px/1.35 var(--serif);
		color: #fff;
		margin-bottom: 6px;
		text-decoration: none;
		cursor: default;
	}
	.def {
		color: #d6dadd;
	}
	span {
		display: block;
		font-size: 12px;
		font-weight: 600;
		color: #a9b0b6;
		margin-bottom: 3px;
	}
	.cues {
		margin-top: 10px;
	}
	.example {
		margin-top: 10px;
		padding-top: 10px;
		border-top: 1px solid rgb(255 255 255 / 0.14);
	}
	.example p {
		font: 14px/1.6 var(--serif);
	}
	mark {
		background: var(--hl-actor);
		color: var(--ink);
		border-radius: 2px;
		padding: 0 2px;
	}
	@keyframes rise {
		from {
			opacity: 0;
			transform: translateY(4px);
		}
	}
	@keyframes drop {
		from {
			opacity: 0;
			transform: translateY(-4px);
		}
	}
</style>
