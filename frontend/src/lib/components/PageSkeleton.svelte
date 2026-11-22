<script lang="ts">
	import Icon from './Icon.svelte';
	import Skeleton from './Skeleton.svelte';
	import { t } from '#lib/i18n/index.svelte.js';

	// A generic page still loading: back link, title, a facts line and a few panels, laid out like a detail page
	// (`cols` puts a narrower column of panels on the right). With `head={false}` only the panels show: the page
	// draws its real header and guide around them, so nothing above moves when the data arrives.
	let { back = '', blocks = 2, cols = false, head = true }: { back?: string; blocks?: number; cols?: boolean; head?: boolean } = $props();
</script>

<div aria-busy="true">
	<span class="visually-hidden" role="status">{t('common.loading')}</span>
	{#if head}
		{#if back}<p class="crumb" aria-hidden="true"><span class="back"><Icon name="back" size={16} />{back}</span></p>{/if}
		<div class="page-head" aria-hidden="true">
			<div class="head">
				<Skeleton width="min(440px, 80%)" height="30px" />
				<span class="facts-ghost"><Skeleton width="120px" height="12px" /><Skeleton width="160px" height="12px" /><Skeleton width="100px" height="12px" /></span>
			</div>
		</div>
	{/if}
	<div class="grid" class:cols aria-hidden="true">
		<div class="stack">
			{#each { length: blocks } as _, i (i)}
				<div class="panel block">
					<Skeleton width="36%" height="16px" />
					<Skeleton lines={i ? 3 : 5} height="12px" gap="12px" last="58%" />
				</div>
			{/each}
		</div>
		{#if cols}
			<div class="panel block">
				<Skeleton width="50%" height="16px" />
				<Skeleton lines={4} height="12px" gap="12px" last="40%" />
			</div>
		{/if}
	</div>
</div>

<style>
	.back {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		color: var(--ink-2);
		font-weight: 500;
	}
	.head {
		display: grid;
		gap: 14px;
		width: 100%;
	}
	.facts-ghost {
		display: flex;
		gap: 22px;
		align-items: center;
		min-height: 23px;
	}
	.grid {
		display: grid;
		gap: var(--space-5);
		align-items: start;
	}
	.grid.cols {
		grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr);
	}
	.stack {
		display: grid;
		gap: var(--space-4);
	}
	.block {
		display: grid;
		gap: 16px;
	}
	@media (max-width: 1000px) {
		.grid.cols {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
