<script lang="ts">
	import PageGuide from '#lib/components/PageGuide.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import Tabs from '#lib/components/Tabs.svelte';
	import Skeleton from '#lib/components/Skeleton.svelte';
	import Overview from '#lib/components/dev/Overview.svelte';
	import Calls from '#lib/components/dev/Calls.svelte';
	import Experiments from '#lib/components/dev/Experiments.svelte';
	import Report from '#lib/components/dev/Report.svelte';
	import Usage from '#lib/components/dev/Usage.svelte';
	import KbStats from '#lib/components/dev/KbStats.svelte';
	import System from '#lib/components/dev/System.svelte';
	import '#lib/components/dev/dev.css';
	import { api } from '#lib/api.js';
	import { t } from '#lib/i18n/index.svelte.js';
	import { session, canMonitor } from '#lib/session.svelte.js';
	import type { MessageKey } from '#lib/i18n/vi.js';
	import type { DevCalls, DevExperiments, DevKb, DevOverview, DevReport, DevSystem, DevUsage } from '#lib/types.js';

	const TABS = ['overview', 'calls', 'experiments', 'report', 'usage', 'kb', 'system'] as const;
	type Tab = (typeof TABS)[number];
	const ENDPOINT: Record<Tab, string> = {
		overview: '/api/dev/overview',
		calls: '/api/dev/calls',
		experiments: '/api/dev/experiments',
		report: '/api/dev/report',
		usage: '/api/dev/usage',
		kb: '/api/dev/kb',
		system: '/api/dev/system'
	};
	const RANGED: Tab[] = ['calls', 'usage'];

	let tab = $state<Tab>('overview');
	let days = $state(14);
	// Each tab keeps the last numbers it loaded (per range), so coming back to a tab shows them at once while
	// a fresh copy loads. The data always travels with the tab that loaded it: a tab never renders another's.
	let loaded = $state<Record<string, unknown>>({});
	const slot = (which: Tab) => (RANGED.includes(which) ? `${which}:${days}` : which);
	const data = $derived(loaded[slot(tab)] ?? null);
	let error = $state('');
	let loading = $state(false);
	let request = 0;

	function fromHash() {
		const name = location.hash.slice(1) as Tab;
		tab = TABS.includes(name) ? name : 'overview';
	}
	$effect(() => {
		fromHash();
		addEventListener('hashchange', fromHash);
		return () => removeEventListener('hashchange', fromHash);
	});

	async function load() {
		const mine = ++request;
		const which = tab;
		loading = true;
		error = '';
		try {
			const value = await api(ENDPOINT[which] + (RANGED.includes(which) ? `?days=${days}` : ''));
			if (mine === request) loaded[slot(which)] = value;
		} catch (e) {
			if (mine === request) error = (e as Error).message;
		} finally {
			if (mine === request) loading = false;
		}
	}
	$effect(() => {
		void tab;
		void days;
		if (canMonitor(session.account)) load();
	});

	function select(next: Tab) {
		history.replaceState(history.state, '', `#${next}`);
	}
</script>

<svelte:head><title>{t('dev.title')} · Lexora</title></svelte:head>

<div class="page">
	{#if !canMonitor(session.account)}
		<h1 class="title">{t('common.forbidden.title')}</h1>
		<p class="lead">{t('common.forbidden.body')}</p>
	{:else}
		<header class="page-head">
			<div>
				<h1 class="title">{t('dev.title')}</h1>
				<p class="lead">{session.account?.role === 'dev' ? t('dev.lead.dev') : t('dev.lead.admin')}</p>
			</div>
			<div class="row">
				{#if RANGED.includes(tab)}
					<div class="segmented" role="group" aria-label={t('dev.range')}>
						{#each [7, 14, 30] as n (n)}<button type="button" aria-pressed={days === n} onclick={() => (days = n)}>{t('dev.days', { n })}</button>{/each}
					</div>
				{/if}
				<button type="button" class="btn quiet" onclick={load} disabled={loading}><Icon name="history" size={16} />{t('dev.refresh')}</button>
			</div>
		</header>
		<PageGuide name="dev" steps={3} />

		<Tabs bind:value={tab} label={t('dev.tabs')} idPrefix="tab" controls="panel" onchange={select} tabs={TABS.map((name) => ({ id: name, label: t(`dev.tab.${name}` as MessageKey) }))} />

		<div class="dev-tab" id="panel" role="tabpanel" aria-labelledby="tab-{tab}" aria-busy={loading}>
			{#if error}
				<p class="notice error" role="alert">{error}</p>
			{:else if !data}
				<span class="visually-hidden" role="status">{t('common.loading')}</span>
				<div class="dev-tiles" aria-hidden="true">
					{#each [0, 1, 2, 3] as i (i)}<div class="dev-tile ghost"><Skeleton width="60%" height="12px" /><Skeleton width="44%" height="26px" /><Skeleton width="70%" height="11px" /></div>{/each}
				</div>
				<div class="panel ghost-panel" aria-hidden="true">
					<Skeleton width="30%" height="16px" />
					<Skeleton width="60%" height="11px" />
					{#each [0, 1, 2, 3] as i (i)}<span class="ghost-row"><Skeleton width="80%" height="12px" /><Skeleton width="60%" height="12px" /><Skeleton width="40%" height="12px" /><Skeleton width="50%" height="12px" /></span>{/each}
				</div>
			{:else if tab === 'overview'}
				<Overview data={data as DevOverview} reload={load} />
			{:else if tab === 'calls'}
				<Calls data={data as DevCalls} />
			{:else if tab === 'experiments'}
				<Experiments data={data as DevExperiments} />
			{:else if tab === 'report'}
				<Report data={data as DevReport} reload={load} />
			{:else if tab === 'usage'}
				<Usage data={data as DevUsage} />
			{:else if tab === 'kb'}
				<KbStats data={data as DevKb} />
			{:else}
				<System data={data as DevSystem} />
			{/if}
		</div>
	{/if}
</div>

<style>
	.page :global(.tabs) {
		margin-bottom: var(--space-5);
	}
	.ghost {
		gap: 10px;
	}
	.ghost-panel {
		display: grid;
		gap: 14px;
	}
	.ghost-row {
		display: grid;
		grid-template-columns: 2fr 2fr 1fr 1fr;
		gap: 16px;
		align-items: center;
		height: 44px;
		border-top: 1px solid var(--rule);
	}
</style>
