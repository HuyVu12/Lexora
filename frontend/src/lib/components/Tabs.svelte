<script lang="ts" generics="K extends string">
	import StepTag from './StepTag.svelte';
	import { reducedMotion } from '#lib/motion.js';

	// Tabs with one ink line under the current tab that slides to the tab you choose (transform only).
	// Arrow keys move between tabs, Home and End jump to the ends; disabled tabs are skipped.
	type Tab = { id: K; label: string; disabled?: boolean; title?: string; step?: number };
	let {
		tabs,
		value = $bindable(),
		label,
		idPrefix = 'tab',
		controls,
		onchange
	}: { tabs: Tab[]; value: K; label: string; idPrefix?: string; controls?: string; onchange?: (id: K) => void } = $props();

	let bar = $state<HTMLElement | null>(null);
	let ink = $state<HTMLElement | null>(null);
	let placed = false;

	function choose(id: K) {
		if (id === value) return;
		value = id;
		onchange?.(id);
	}

	function place(animated: boolean) {
		if (!bar || !ink) return;
		const button = bar.querySelector<HTMLElement>(`[role='tab'][aria-selected='true']`);
		if (!button) {
			ink.style.opacity = '0';
			return;
		}
		const moving = animated && placed && !reducedMotion();
		ink.style.transition = moving ? 'transform var(--dur-base) var(--ease-out)' : 'none';
		ink.style.transform = `translateX(${button.offsetLeft}px) scaleX(${button.offsetWidth})`;
		ink.style.opacity = '1';
		placed = true;
	}

	$effect(() => {
		void value;
		void tabs;
		place(true);
	});

	// Labels change width with the language, the step badges and the fonts loading: follow them without motion.
	$effect(() => {
		if (!bar) return;
		const observer = new ResizeObserver(() => place(false));
		for (const button of bar.querySelectorAll('[role=tab]')) observer.observe(button);
		return () => observer.disconnect();
	});

	function keys(event: KeyboardEvent) {
		const enabled = tabs.filter((tab) => !tab.disabled);
		const at = enabled.findIndex((tab) => tab.id === value);
		let next: Tab | undefined;
		if (event.key === 'ArrowRight') next = enabled[(at + 1) % enabled.length];
		else if (event.key === 'ArrowLeft') next = enabled[(at - 1 + enabled.length) % enabled.length];
		else if (event.key === 'Home') next = enabled[0];
		else if (event.key === 'End') next = enabled[enabled.length - 1];
		if (!next) return;
		event.preventDefault();
		choose(next.id);
		document.getElementById(`${idPrefix}-${next.id}`)?.focus();
	}
</script>

<div class="tabs" role="tablist" aria-label={label} tabindex="-1" bind:this={bar} onkeydown={keys}>
	{#each tabs as tab (tab.id)}
		<button
			type="button"
			role="tab"
			id="{idPrefix}-{tab.id}"
			aria-selected={value === tab.id}
			aria-controls={controls}
			tabindex={value === tab.id ? 0 : -1}
			disabled={tab.disabled}
			title={tab.title || undefined}
			onclick={() => choose(tab.id)}>{#if tab.step}<StepTag n={tab.step} compact />{/if}{tab.label}</button>
	{/each}
	<span class="ink" bind:this={ink} aria-hidden="true"></span>
</div>

<style>
	.tabs {
		position: relative;
		display: flex;
		gap: 4px;
		border-bottom: 1px solid var(--rule);
		overflow-x: auto;
		scrollbar-width: none;
	}
	.tabs:focus {
		outline: none;
	}
	button {
		display: inline-flex;
		align-items: center;
		border: 0;
		background: none;
		padding: 10px 12px 11px;
		font: inherit;
		font-weight: 500;
		color: var(--muted);
		white-space: nowrap;
		cursor: pointer;
		transition: color var(--dur-fast) ease;
	}
	@media (hover: hover) {
		button:hover:not(:disabled) {
			color: var(--ink);
		}
	}
	button[aria-selected='true'] {
		color: var(--ink);
	}
	button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	button:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: -4px;
		border-radius: 6px;
	}
	/* 1px wide and scaled to the tab's width: the line moves with transform alone. */
	.ink {
		position: absolute;
		left: 0;
		bottom: 0;
		width: 1px;
		height: 2px;
		background: var(--graphite);
		transform-origin: 0 0;
		opacity: 0;
		pointer-events: none;
	}
</style>
