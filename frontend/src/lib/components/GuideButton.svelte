<script lang="ts">
	import { tick } from 'svelte';
	import Icon from './Icon.svelte';
	import { t } from '#lib/i18n/index.svelte.js';
	import { pop, popOut } from '#lib/motion.js';
	import { tourStatus, startTour } from '#lib/tour/tour.svelte.js';
	import { TOURS } from '#lib/tour/tours/index.js';

	// The "?" beside a page title. PageGuide mounts it into the title, so it carries no text node: the heading's
	// text stays exactly the page name. On a page with a step-by-step tour it opens a small menu (short guide or
	// step by step); elsewhere it opens and closes the page guide directly. The menu is moved to <body>, so the
	// heading never contains it.
	let {
		open,
		label,
		hint,
		controls,
		ontoggle,
		tourId = null
	}: { open: boolean; label: string; hint: string; controls: string; ontoggle: () => void; tourId?: string | null } = $props();

	const offered = $derived(tourId ? (TOURS.find((x) => x.id === tourId) ?? null) : null);
	const seen = $derived(offered ? tourStatus(offered.id) : 'new');
	let menu = $state(false);
	let at = $state({ x: 0, y: 0 });
	let button = $state<HTMLButtonElement | null>(null);
	let list = $state<HTMLElement | null>(null);

	async function press() {
		if (!offered) return ontoggle();
		if (menu) return (menu = false);
		const box = button!.getBoundingClientRect();
		at = { x: Math.max(8, Math.min(box.left, document.documentElement.clientWidth - 248)), y: box.bottom + 8 };
		menu = true;
		await tick();
		list?.querySelector<HTMLElement>('[role="menuitem"]')?.focus();
	}

	function choose(action: () => void) {
		menu = false;
		action();
	}

	function keys(event: KeyboardEvent) {
		const items = [...(list?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [])];
		const i = items.indexOf(document.activeElement as HTMLElement);
		if (event.key === 'Escape') {
			event.preventDefault();
			event.stopPropagation();
			menu = false;
			button?.focus();
		} else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
			event.preventDefault();
			items[(i + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length]?.focus();
		} else if (event.key === 'Tab') {
			menu = false;
		}
	}

	function outside(event: Event) {
		if (menu && !list?.contains(event.target as Node) && !button?.contains(event.target as Node)) menu = false;
	}

	/** Attachment: the menu lives at the end of <body>, outside the heading. */
	const toBody = (node: HTMLElement) => {
		document.body.appendChild(node);
		return () => node.remove();
	};
</script>

<svelte:window onpointerdown={outside} onscroll={() => (menu = false)} onresize={() => (menu = false)} />

<button
	type="button"
	class="guide-q"
	class:open
	class:menu-open={menu}
	bind:this={button}
	data-tour="guide-button"
	aria-label={label}
	title={offered ? label : hint}
	aria-haspopup={offered ? 'menu' : undefined}
	aria-expanded={offered ? menu : open}
	aria-controls={offered ? (menu ? 'guide-menu' : undefined) : controls}
	onclick={press}
>
	<Icon name="help" size={16} />
</button>

{#if menu && offered}
	<div class="guide-menu" id="guide-menu" role="menu" tabindex="-1" aria-label={label} bind:this={list} style:left="{at.x}px" style:top="{at.y}px"
		onkeydown={keys} {@attach toBody} in:pop={{ origin: 'top left' }} out:popOut>
		<button type="button" role="menuitem" class="item" onclick={() => choose(ontoggle)}>
			<Icon name="help" size={16} /><span>{open ? t('tour.menu.shortHide') : t('tour.menu.short')}</span>
		</button>
		<button type="button" role="menuitem" class="item" onclick={() => choose(() => startTour(offered.id))}>
			<Icon name="route" size={16} /><span>{t('tour.menu.steps')}<small>{t(offered.title)}</small></span>
			{#if seen === 'done'}<span class="seen" title={t('tour.menu.done')}><Icon name="check" size={14} /><span class="visually-hidden">{t('tour.menu.done')}</span></span>{/if}
		</button>
	</div>
{/if}

<style>
	.guide-q {
		display: inline-grid;
		place-items: center;
		width: 26px;
		height: 26px;
		margin: 0 0 0 10px;
		padding: 0;
		vertical-align: 0.18em;
		border: 1px solid var(--rule-strong);
		border-radius: 50%;
		background: var(--paper);
		color: var(--ink-2);
		cursor: pointer;
		transition:
			background-color var(--dur-fast) ease,
			border-color var(--dur-fast) ease,
			color var(--dur-fast) ease,
			transform var(--dur-fast) var(--ease-out);
	}
	.guide-q :global(svg) {
		stroke-width: 2.2;
	}
	@media (hover: hover) {
		.guide-q:hover {
			border-color: var(--flag);
			color: var(--flag);
		}
	}
	.guide-q:active {
		transform: scale(0.92);
		transition-duration: var(--dur-press);
	}
	.guide-q.open,
	.guide-q.menu-open {
		background: var(--flag);
		border-color: var(--flag);
		color: var(--paper);
	}
	.guide-q:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	.guide-menu {
		position: fixed;
		z-index: 60;
		width: 240px;
		padding: 6px;
		display: grid;
		gap: 2px;
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: var(--r-panel);
		box-shadow: var(--shadow-pop);
		font: 500 14px/1.35 var(--sans);
		letter-spacing: normal;
		color: var(--ink-2);
	}
	.item {
		display: flex;
		align-items: center;
		gap: 10px;
		min-height: 38px;
		padding: 6px 10px;
		border: 0;
		border-radius: var(--r-control);
		background: none;
		color: inherit;
		font: inherit;
		text-align: left;
		cursor: pointer;
		transition: background-color var(--dur-fast) ease;
	}
	.item > span:not(.seen) {
		display: grid;
		flex: 1;
		min-width: 0;
	}
	.item small {
		font-size: 12.5px;
		font-weight: 400;
		color: var(--muted);
	}
	.item :global(svg) {
		flex: none;
		color: var(--flag);
	}
	.item:hover,
	.item:focus-visible {
		background: var(--desk);
		color: var(--ink);
		outline: none;
	}
	.seen :global(svg) {
		color: var(--approve);
	}
</style>
