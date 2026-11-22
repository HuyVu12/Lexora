<script lang="ts">
	import { t } from '#lib/i18n/index.svelte.js';
	import { guide } from '#lib/guide.svelte.js';

	// "Step N" on a page section, numbered like the steps of the page's PageGuide.
	// `compact` shows only the number (for tabs and buttons); screen readers still hear "Step N".
	// Badges belong to the guide: they show while it is open and leave with it, so a page whose guide is
	// closed carries no extra labels.
	let { n, compact = false }: { n: number; compact?: boolean } = $props();
</script>

{#if !guide.open}
	<!-- Guide hidden: no badge. -->
{:else if compact}
	<span class="step-tag compact" aria-label={t('guide.step', { n })} role="img">{n}</span>
{:else}
	<span class="step-tag">{t('guide.step', { n })}</span>
{/if}

<style>
	.step-tag {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		margin-right: 8px;
		padding: 0 7px;
		height: 20px;
		border-radius: 999px;
		border: 1px solid #c3d2f1;
		background: #eef3fd;
		color: var(--flag);
		font-size: 11.5px;
		font-weight: 600;
		letter-spacing: 0.01em;
		vertical-align: 2px;
		white-space: nowrap;
		animation: tag-in var(--dur-base) var(--ease-out) both;
	}
	.compact {
		width: 18px;
		height: 18px;
		padding: 0;
		margin-right: 6px;
		border: 0;
		background: var(--flag);
		color: var(--paper);
		font-size: 11px;
		vertical-align: 1px;
	}
	@keyframes tag-in {
		from {
			opacity: 0;
			transform: scale(0.85);
		}
	}
</style>
