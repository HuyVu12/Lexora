<script lang="ts">
	import { toast } from '#lib/toast.svelte.js';
	import { t } from '#lib/i18n/index.svelte.js';
	import Icon from './Icon.svelte';
	const text = $derived(toast.message === null ? '' : typeof toast.message === 'string' ? toast.message : t(toast.message.key, toast.message.params));
</script>

<div class="toast-region" role="status" aria-live="polite">
	{#if text}
		{#key toast.id}
			<div class="toast" class:error={toast.error}>
				<span>{text}</span>
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
		width: max-content;
		max-width: min(640px, calc(100vw - 32px));
	}
	.toast {
		display: flex;
		gap: 14px;
		align-items: center;
		padding: 10px 10px 10px 18px;
		background: var(--graphite);
		color: #fff;
		border-radius: 10px;
		box-shadow: var(--shadow-pop);
		animation: in 0.25s var(--ease-out);
	}
	.toast.error {
		background: var(--reject);
	}
	button {
		border: 0;
		background: transparent;
		color: inherit;
		display: grid;
		place-items: center;
		width: 32px;
		height: 32px;
		border-radius: 6px;
		cursor: pointer;
	}
	button:hover {
		background: rgb(255 255 255 / 0.14);
	}
	@keyframes in {
		from {
			opacity: 0;
			transform: translateY(8px);
		}
	}
</style>
