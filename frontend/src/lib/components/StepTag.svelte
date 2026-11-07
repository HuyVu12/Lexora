<script lang="ts">
	import { t } from '#lib/i18n/index.svelte.js';
	import { guide } from '#lib/guide.svelte.js';

	// "Step N" on a page section, numbered like the steps of the page's PageGuide.
	// `compact` shows only the number (for tabs and buttons); screen readers still hear "Step N".
	// Badges show only while the page guide is open.
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
		padding: 1px 8px;
		border-radius: 999px;
		background: var(--flag);
		color: var(--paper);
		font-size: 12px;
		font-weight: 700;
		letter-spacing: 0.01em;
		vertical-align: 2px;
		white-space: nowrap;
	}
	.compact {
		width: 18px;
		height: 18px;
		padding: 0;
		margin-right: 6px;
		font-size: 11px;
		vertical-align: 1px;
	}
</style>
