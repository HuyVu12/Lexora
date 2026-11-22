<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';
	import { t } from '#lib/i18n/index.svelte.js';

	// A modal question before an outward action (a model call, a network fetch). Escape and Cancel close it.
	let { open = $bindable(false), title, confirmLabel, onconfirm, children }: { open: boolean; title: string; confirmLabel: string; onconfirm: () => void; children: Snippet } =
		$props();
	let dialog = $state<HTMLDialogElement | null>(null);

	$effect(() => {
		if (!dialog) return;
		if (open && !dialog.open) dialog.showModal();
		if (!open && dialog.open) dialog.close();
	});
</script>

<dialog bind:this={dialog} aria-labelledby="confirm-title" onclose={() => (open = false)}>
	<h2 class="heading" id="confirm-title">{title}</h2>
	{@render children()}
	<div class="row actions">
		<button type="button" class="btn quiet" onclick={() => (open = false)}>{t('common.cancel')}</button>
		<button type="button" class="btn primary" onclick={() => { open = false; onconfirm(); }}><Icon name="check" />{confirmLabel}</button>
	</div>
</dialog>

<style>
	/* Opens with a short rise and scale from the centre (a modal is not anchored to its trigger) and closes faster.
	 * @starting-style and allow-discrete let CSS animate both ways of a native <dialog>. */
	dialog {
		max-width: 540px;
		width: calc(100% - 32px);
		border: 1px solid var(--rule);
		border-radius: var(--r-panel);
		padding: 22px 24px;
		box-shadow: var(--shadow-pop);
		color: var(--ink);
		opacity: 0;
		transform: translateY(6px) scale(0.98);
		transition:
			opacity var(--dur-fast) ease,
			transform var(--dur-fast) var(--ease-out),
			overlay var(--dur-fast) allow-discrete,
			display var(--dur-fast) allow-discrete;
	}
	dialog[open] {
		opacity: 1;
		transform: none;
		transition-duration: var(--dur-base);
	}
	@starting-style {
		dialog[open] {
			opacity: 0;
			transform: translateY(10px) scale(0.97);
		}
	}
	dialog::backdrop {
		background: rgb(20 22 24 / 0);
		transition:
			background-color var(--dur-fast) ease,
			overlay var(--dur-fast) allow-discrete,
			display var(--dur-fast) allow-discrete;
	}
	dialog[open]::backdrop {
		background: rgb(20 22 24 / 0.35);
		transition-duration: var(--dur-base);
	}
	@starting-style {
		dialog[open]::backdrop {
			background: rgb(20 22 24 / 0);
		}
	}
	.actions {
		justify-content: flex-end;
		gap: 10px;
		margin-top: 12px;
	}
</style>
