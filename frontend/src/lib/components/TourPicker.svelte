<script lang="ts">
	import Icon from './Icon.svelte';
	import { t } from '#lib/i18n/index.svelte.js';
	import { tourStatus, toursHere, TOUR_AREAS } from '#lib/tour/tour.svelte.js';
	import type { Tour } from '#lib/tour/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';
	import type { Role } from '#lib/types.js';

	// The user menu's list of step-by-step tours, opened from its single "Hướng dẫn từng bước" item so the menu
	// itself stays short: the tour about the open page first (with its one-line summary), then the others grouped
	// by area, each with its finished mark. `tours` is already filtered by role.
	let {
		tours,
		role,
		path,
		onpick,
		onback
	}: { tours: Tour[]; role: Role | null; path: string; onpick: (id: string) => void; onback: () => void } = $props();

	const here = $derived(toursHere(role, path));
	const groups = $derived(
		TOUR_AREAS.map((area) => ({ area, items: tours.filter((x) => x.area === area && !here.includes(x)) })).filter((g) => g.items.length)
	);
	const seen = $derived(tours.filter((x) => tourStatus(x.id) === 'done').length);

	let back = $state<HTMLButtonElement | null>(null);
	// Keyboard users land on the way back; the list follows in tab order.
	$effect(() => back?.focus({ preventScroll: true }));
</script>

<div class="tour-picker">
	<div class="picker-head">
		<button bind:this={back} type="button" class="back" aria-label={t('tour.menu.back')} title={t('tour.menu.back')} onclick={onback}><Icon name="back" size={16} /></button>
		<strong id="tour-picker-title">{t('tour.menu.title')}</strong>
		<span class="count">{t('tour.menu.seen', { done: seen, n: tours.length })}</span>
	</div>
	<div class="picker-list" role="group" aria-labelledby="tour-picker-title">
		{#if here.length}
			<div class="group here">
				<p class="label">{t('tour.menu.here')}</p>
				{#each here as item (item.id)}{@render row(item, true)}{/each}
			</div>
		{/if}
		{#each groups as g (g.area)}
			<div class="group">
				<p class="label">{t(`tour.area.${g.area}` as MessageKey)}</p>
				{#each g.items as item (item.id)}{@render row(item, false)}{/each}
			</div>
		{/each}
	</div>
</div>

{#snippet row(item: Tour, current: boolean)}
	{@const mark = tourStatus(item.id)}
	<button type="button" class="pick" class:current onclick={() => onpick(item.id)}>
		<Icon name="route" size={16} />
		<span class="name">{t(item.title)}{#if current}<small>{t(item.summary)}</small>{/if}</span>
		{#if mark === 'done'}
			<span class="mark-done" title={t('tour.menu.done')}><Icon name="check" size={14} /><span class="visually-hidden">{t('tour.menu.done')}</span></span>
		{:else if mark === 'progress'}
			<span class="mark-progress">{t('tour.menu.progress')}</span>
		{/if}
	</button>
{/snippet}

<style>
	.tour-picker {
		display: grid;
		min-height: 0;
	}
	.picker-head {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto;
		align-items: center;
		gap: 6px;
		padding: 0 4px 6px 0;
		margin-bottom: 2px;
		border-bottom: 1px solid var(--rule);
	}
	.picker-head strong {
		font-weight: 600;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.count {
		font-size: 12.5px;
		color: var(--muted);
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}
	.back {
		display: grid;
		place-items: center;
		width: 32px;
		height: 32px;
		border: 0;
		border-radius: var(--r-control);
		background: none;
		color: var(--ink-2);
		cursor: pointer;
		transition: background-color var(--dur-fast) ease;
	}
	.back:hover {
		background: var(--desk);
		color: var(--ink);
	}
	/* Long lists scroll inside the menu instead of running off a short window. */
	.picker-list {
		display: grid;
		gap: 2px;
		max-height: calc(100dvh - var(--topbar) - 120px);
		overflow-y: auto;
		overscroll-behavior: contain;
	}
	.group {
		display: grid;
		gap: 1px;
		padding-top: 4px;
	}
	.group .label {
		padding: 4px 10px 2px;
		font-size: 12px;
	}
	.pick {
		display: flex;
		align-items: center;
		gap: 10px;
		min-height: 34px;
		padding: 4px 10px;
		border: 0;
		border-radius: var(--r-control);
		background: none;
		color: var(--ink-2);
		font: inherit;
		font-weight: 500;
		text-align: left;
		cursor: pointer;
		transition: background-color var(--dur-fast) ease;
	}
	.pick:hover {
		background: var(--desk);
		color: var(--ink);
	}
	.pick :global(svg) {
		flex: none;
		color: var(--flag);
	}
	.name {
		flex: 1;
		min-width: 0;
		display: grid;
		line-height: 1.35;
	}
	.name small {
		font-size: 12.5px;
		font-weight: 400;
		color: var(--muted);
	}
	/* The tour for the open page: tinted like the page guide that also offers it. */
	.pick.current {
		align-items: flex-start;
		padding: 8px 10px;
		background: #f3f6fd;
	}
	.pick.current:hover {
		background: rgb(47 95 196 / 0.1);
	}
	.pick.current :global(svg) {
		margin-top: 2px;
	}
	.mark-done :global(svg) {
		color: var(--approve);
	}
	.mark-progress {
		flex: none;
		font-size: 12px;
		font-weight: 400;
		color: var(--muted);
		white-space: nowrap;
	}
	.back:focus-visible,
	.pick:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: -2px;
	}
</style>
