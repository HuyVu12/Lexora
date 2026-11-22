<script module lang="ts">
	export interface RailItem {
		key: string;
		/** Number shown in front of the item (its place in the whole set). */
		n: number;
		text: string;
		done: boolean;
		/** Screen-reader status of the item ("Done", "To do", "2 norms"). */
		status: string;
		/** A small green dot after the number, with its screen-reader meaning. */
		dot?: string;
	}
</script>

<script lang="ts" generics="T extends RailItem">
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';
	import { reducedMotion } from '#lib/motion.js';

	// The item list of an annotation workspace: a sticky panel as tall as the window (header included, see
	// workspace.css), a progress count, a current-item marker that glides when you click another item and jumps
	// when you save and move on (fast keyboard work never waits for motion), done and to-do markers, the current
	// item kept in view, and soft fades at the list's edges where more items are scrolled out of sight.
	let {
		heading,
		items,
		selected,
		onpick,
		done,
		total,
		progress,
		empty = '',
		head,
		foot,
		marker
	}: {
		heading: string;
		items: T[];
		selected: string;
		onpick: (key: string) => void;
		done: number;
		total: number;
		/** Spoken meaning of the progress bar, e.g. "You labelled 12/290 sentences". */
		progress: string;
		empty?: string;
		/** Controls between the progress and the list (a scope switch, a batch action). */
		head?: Snippet;
		/** Tools under the list. */
		foot?: Snippet;
		/** Replaces the done/to-do marker at the end of a row. */
		marker?: Snippet<[T]>;
	} = $props();

	let scroller = $state<HTMLElement | null>(null);
	let cursor = $state<HTMLElement | null>(null);
	let glide = false;
	let more = $state({ above: false, below: false });

	function edges() {
		if (!scroller) return;
		const { scrollTop, clientHeight, scrollHeight } = scroller;
		more.above = scrollTop > 2;
		more.below = scrollTop + clientHeight < scrollHeight - 2;
	}
	$effect(() => {
		if (!scroller) return;
		const observer = new ResizeObserver(edges);
		observer.observe(scroller);
		return () => observer.disconnect();
	});

	function choose(key: string) {
		glide = key !== selected;
		onpick(key);
	}

	$effect(() => {
		const key = selected;
		void items;
		if (!scroller || !cursor) return;
		const row = [...scroller.querySelectorAll<HTMLElement>('li[data-key]')].find((el) => el.dataset.key === key);
		if (!row) {
			cursor.style.opacity = '0';
			return;
		}
		const y = row.offsetTop;
		const moving = glide && !reducedMotion() && cursor.style.opacity === '1';
		cursor.style.transition = moving ? 'transform var(--dur-base) var(--ease-out)' : 'none';
		cursor.style.height = `${row.offsetHeight}px`;
		cursor.style.transform = `translateY(${y}px)`;
		cursor.style.opacity = '1';
		glide = false;
		// Keep the current row in view inside the list, without scrolling the page.
		// The margins clear the edge fades, so the current row is never the faded one.
		const above = 28;
		const below = 60;
		if (y < scroller.scrollTop + above) scroller.scrollTop = Math.max(0, y - above);
		else if (y + row.offsetHeight > scroller.scrollTop + scroller.clientHeight - below) scroller.scrollTop = y + row.offsetHeight - scroller.clientHeight + below;
		edges();
	});
</script>

<section class="panel rail" aria-labelledby="rail-heading" data-tour="item-rail">
	<div class="top">
		<div class="head">
			<h2 class="heading" id="rail-heading">{heading}</h2>
			<span class="count" aria-hidden="true"><strong>{done}</strong> / {total}</span>
		</div>
		<span class="meter" role="progressbar" aria-label={progress} aria-valuemin={0} aria-valuemax={total} aria-valuenow={done} title={progress}>
			<i style:transform="scaleX({total ? Math.min(done, total) / total : 0})"></i>
		</span>
		{@render head?.()}
	</div>
	{#if items.length}
		<div class="list">
		<span class="fade top" class:on={more.above} aria-hidden="true"></span>
		<span class="fade bottom" class:on={more.below} aria-hidden="true"></span>
		<div class="scroller" bind:this={scroller} onscroll={edges}>
			<span class="cursor" bind:this={cursor} aria-hidden="true"></span>
			<ol class="rail-items">
				{#each items as item (item.key)}
					<li data-key={item.key}>
						<button type="button" class="rail-item" aria-current={item.key === selected ? 'true' : undefined} onclick={() => choose(item.key)}>
							<span class="num">{item.n}{#if item.dot}<span class="dot" aria-hidden="true"></span><span class="visually-hidden">{item.dot}</span>{/if}</span>
							<span class="text">{item.text}</span>
							<span class="state">
								{#if marker}{@render marker(item)}{:else}<span class="tick" class:on={item.done} aria-hidden="true">{#if item.done}<Icon name="check" size={12} />{/if}</span>{/if}
								<span class="visually-hidden">{item.status}</span>
							</span>
						</button>
					</li>
				{/each}
			</ol>
		</div>
		</div>
	{:else if empty}
		<p class="small muted none">{empty}</p>
	{/if}
	{#if foot}<div class="foot">{@render foot()}</div>{/if}
</section>

<style>
	.rail {
		position: sticky;
		top: calc(var(--topbar) + var(--space-4));
		max-height: var(--ws-h, calc(100dvh - var(--topbar) - var(--space-8)));
		display: flex;
		flex-direction: column;
		padding: 0;
		overflow: hidden;
	}
	.top {
		display: grid;
		gap: 10px;
		padding: 18px 20px 12px;
		border-bottom: 1px solid var(--rule);
	}
	.head {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: 12px;
	}
	.count {
		font-size: 13.5px;
		color: var(--muted);
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}
	.count strong {
		color: var(--ink);
		font-weight: 600;
	}
	.meter {
		height: 4px;
	}
	/* The list scrolls on its own. Where items are scrolled out of sight, the edge fades into the paper instead of
	 * cutting a row in half; the fades stop short of the scrollbar so it stays crisp. */
	.list {
		position: relative;
		flex: 1;
		min-height: 0;
		display: flex;
		flex-direction: column;
	}
	.scroller {
		position: relative;
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		overscroll-behavior: contain;
		padding: 6px 8px;
	}
	.fade {
		position: absolute;
		z-index: 1;
		left: 0;
		right: 14px;
		pointer-events: none;
		opacity: 0;
		transition: opacity var(--dur-fast) ease;
	}
	.fade.on {
		opacity: 1;
	}
	.fade.top {
		top: 0;
		height: 24px;
		background: linear-gradient(var(--paper), rgb(255 255 255 / 0));
	}
	.fade.bottom {
		bottom: 0;
		height: 56px;
		background: linear-gradient(rgb(255 255 255 / 0), var(--paper) 85%);
	}
	.cursor {
		position: absolute;
		top: 0;
		left: 8px;
		right: 8px;
		border-radius: var(--r-control);
		background: var(--desk);
		box-shadow: inset 3px 0 0 var(--graphite);
		opacity: 0;
		pointer-events: none;
		will-change: transform;
	}
	.rail-items {
		position: relative;
		list-style: none;
		margin: 0;
		padding: 0;
	}
	/* Every row is two lines tall, so the list keeps one rhythm and the marker never changes size. */
	.rail-item {
		width: 100%;
		height: 60px;
		display: grid;
		grid-template-columns: 2.25rem minmax(0, 1fr) minmax(20px, auto);
		gap: 10px;
		align-items: center;
		padding: 0 12px 0 14px;
		border: 0;
		border-radius: var(--r-control);
		background: none;
		text-align: left;
		font: inherit;
		font-size: 14px;
		line-height: 1.45;
		color: var(--ink-2);
		cursor: pointer;
		transition: background-color var(--dur-fast) ease;
	}
	@media (hover: hover) {
		.rail-item:hover:not([aria-current='true']) {
			background: rgb(231 232 231 / 0.55);
		}
	}
	.rail-item[aria-current='true'] {
		color: var(--ink);
	}
	.rail-item:focus-visible {
		outline-offset: -2px;
	}
	.num {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		color: var(--muted);
		font-size: 13px;
		font-variant-numeric: tabular-nums;
	}
	.rail-item[aria-current='true'] .num {
		color: var(--ink);
		font-weight: 600;
	}
	.dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--approve);
		flex: none;
	}
	.text {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	.state {
		display: grid;
		justify-items: end;
	}
	.tick {
		display: grid;
		place-items: center;
		width: 18px;
		height: 18px;
		border-radius: 50%;
		border: 1.5px solid var(--rule-strong);
		color: var(--paper);
	}
	.tick.on {
		border-color: var(--approve);
		background: var(--approve);
	}
	.tick :global(svg) {
		stroke-width: 3;
	}
	.none {
		padding: 16px 20px;
	}
	.foot {
		display: grid;
		gap: 8px;
		padding: 12px 16px 16px;
		border-top: 1px solid var(--rule);
	}
	/* A page may pass tools that are all hidden for now (nothing to compare yet): no empty strip then. */
	.foot:not(:has(:global(*))) {
		display: none;
	}
	@media (max-width: 1000px) {
		.rail {
			position: static;
			max-height: 400px;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.fade {
			transition: none;
		}
	}
</style>
