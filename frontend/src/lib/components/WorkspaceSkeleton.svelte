<script lang="ts">
	import Skeleton from './Skeleton.svelte';
	import { t } from '#lib/i18n/index.svelte.js';
	import './workspace.css';

	// The body of an annotation workspace while its set loads: the item rail and the work panel, each where the
	// real one will be. The page draws its own back link, header and guide around it, so nothing jumps.
	let { tabs = 2, rows = 9 }: { tabs?: number; rows?: number } = $props();
</script>

<div class="ws-cols" aria-busy="true">
	<span class="visually-hidden" role="status">{t('common.loading')}</span>
	<div class="panel ghost-rail" aria-hidden="true">
		<div class="ghost-top">
			<span class="ghost-row"><Skeleton width="90px" height="16px" /><Skeleton width="54px" height="12px" /></span>
			<Skeleton height="4px" radius="2px" />
		</div>
		<div class="ghost-items">
			{#each { length: rows } as _, i (i)}
				<span class="ghost-item"><Skeleton width="18px" height="11px" /><Skeleton lines={2} height="11px" gap="8px" last={i % 3 === 1 ? '40%' : '72%'} /><Skeleton width="18px" height="18px" radius="50%" /></span>
			{/each}
		</div>
	</div>
	<div class="panel ws-work ghost-work" aria-hidden="true">
		{#if tabs}<span class="ghost-tabs">{#each { length: tabs } as _, i (i)}<Skeleton width="96px" height="14px" />{/each}</span>{/if}
		<div class="ws-item">
			<span class="ghost-row"><Skeleton width="45%" height="14px" /><Skeleton width="70px" height="20px" radius="999px" /></span>
			<Skeleton width="60%" height="11px" />
			<Skeleton lines={3} height="18px" gap="14px" last="55%" />
		</div>
		<Skeleton lines={2} height="12px" gap="10px" last="40%" />
		<span class="ghost-row end"><Skeleton width="110px" height="38px" radius="6px" /><Skeleton width="150px" height="38px" radius="6px" /></span>
	</div>
</div>

<style>
	.ghost-rail {
		padding: 0;
		overflow: hidden;
	}
	.ghost-top {
		display: grid;
		gap: 14px;
		padding: 20px 20px 14px;
		border-bottom: 1px solid var(--rule);
	}
	.ghost-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 12px;
	}
	.ghost-row.end {
		justify-content: flex-end;
	}
	.ghost-items {
		display: grid;
		padding: 6px 8px;
	}
	.ghost-item {
		height: 60px;
		display: grid;
		grid-template-columns: 2.25rem minmax(0, 1fr) 20px;
		gap: 10px;
		align-items: center;
		padding: 0 12px 0 14px;
	}
	.ghost-work {
		gap: var(--space-5);
	}
	.ghost-work:has(.ghost-tabs) {
		padding-top: 6px;
	}
	.ghost-tabs {
		display: flex;
		gap: 26px;
		margin: 0 -24px;
		padding: 13px 26px 14px;
		border-bottom: 1px solid var(--rule);
	}
</style>
