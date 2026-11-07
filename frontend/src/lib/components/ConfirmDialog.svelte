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
	dialog {
		max-width: 540px;
		width: calc(100% - 32px);
		border: 1px solid var(--rule);
		border-radius: var(--r-panel);
		padding: 22px 24px;
		box-shadow: var(--shadow-pop);
		color: var(--ink);
	}
	dialog::backdrop {
		background: rgb(20 22 24 / 0.35);
	}
	.actions {
		justify-content: flex-end;
		gap: 10px;
		margin-top: 12px;
	}
</style>
