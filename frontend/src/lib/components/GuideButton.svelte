<script lang="ts">
	import Icon from './Icon.svelte';

	// The "?" beside a page title that opens and closes the page guide. PageGuide mounts it into the title,
	// so it carries no text node: the heading's text stays exactly the page name.
	let { open, label, hint, controls, ontoggle }: { open: boolean; label: string; hint: string; controls: string; ontoggle: () => void } = $props();
</script>

<button type="button" class="guide-q" class:open aria-label={label} title={hint} aria-expanded={open} aria-controls={controls} onclick={ontoggle}>
	<Icon name="help" size={16} />
</button>

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
	.guide-q.open {
		background: var(--flag);
		border-color: var(--flag);
		color: var(--paper);
	}
	.guide-q:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
</style>
