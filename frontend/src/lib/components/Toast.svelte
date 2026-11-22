<script lang="ts">
	import { toast, pauseToast, resumeToast } from '#lib/toast.svelte.js';
	import { t } from '#lib/i18n/index.svelte.js';
	import { pop, popOut } from '#lib/motion.js';
	import Icon from './Icon.svelte';
	const text = $derived(toast.message === null ? '' : typeof toast.message === 'string' ? toast.message : t(toast.message.key, toast.message.params));

	// Rises from the bottom edge with a little spring and leaves faster than it came. A new message replaces the
	// old one in the same spot (both share one grid cell while they cross). Hovering, focusing or hiding the tab
	// holds the timer, so a message being read never vanishes under the pointer.
	function visibility() {
		if (document.hidden) pauseToast();
		else resumeToast();
	}
</script>

<svelte:document onvisibilitychange={visibility} />

<div class="toast-region" role="status" aria-live="polite">
	{#if text}
		{#key toast.id}
			<div
				class="toast"
				class:error={toast.error}
				role="presentation"
				in:pop={{ origin: 'bottom center', y: 14, scale: 0.94 }}
				out:popOut={{ y: 6, scale: 0.98 }}
				onpointerenter={pauseToast}
				onpointerleave={resumeToast}
				onfocusin={pauseToast}
				onfocusout={resumeToast}
			>
				<Icon name={toast.error ? 'warn' : 'check'} size={17} />
				<span class="text">{text}</span>
				<button type="button" aria-label={t('common.dismiss')} onclick={() => (toast.message = null)}><Icon name="x" size={16} /></button>
			</div>
		{/key}
	{/if}
</div>

<style>
	.toast-region {
		position: fixed;
		left: 50%;
		bottom: 24px;
		transform: translateX(-50%);
		z-index: 90;
		display: grid;
		justify-items: center;
		width: max-content;
		max-width: min(640px, calc(100vw - 32px));
	}
	.toast {
		grid-area: 1 / 1;
		display: flex;
		gap: 10px;
		align-items: center;
		padding: 8px 8px 8px 14px;
		background: var(--graphite);
		color: #fff;
		border-radius: 10px;
		box-shadow: var(--shadow-pop);
	}
	.toast > :global(svg:first-child) {
		flex: none;
		color: #9fd8b1;
	}
	.toast.error {
		background: var(--reject);
	}
	.toast.error > :global(svg:first-child) {
		color: #fff;
	}
	.text {
		padding: 2px 4px 2px 0;
	}
	button {
		flex: none;
		border: 0;
		background: transparent;
		color: inherit;
		display: grid;
		place-items: center;
		width: 32px;
		height: 32px;
		border-radius: 6px;
		cursor: pointer;
		transition: background-color var(--dur-fast) ease;
	}
	button:hover {
		background: rgb(255 255 255 / 0.14);
	}
</style>
