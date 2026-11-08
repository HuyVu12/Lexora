<script lang="ts">
	import PageGuide from '#lib/components/PageGuide.svelte';
	import Icon from '#lib/components/Icon.svelte';
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
	// The data always travels with the tab that loaded it, so a tab never renders another tab's numbers.
	let loaded = $state<{ tab: Tab; value: unknown } | null>(null);
	const data = $derived(loaded && loaded.tab === tab ? loaded.value : null);
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
			if (mine === request) loaded = { tab: which, value };
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
		tab = next;
	}
	function keys(event: KeyboardEvent) {
		const at = TABS.indexOf(tab);
		const next = event.key === 'ArrowRight' ? TABS[(at + 1) % TABS.length] : event.key === 'ArrowLeft' ? TABS[(at - 1 + TABS.length) % TABS.length] : null;
		if (next) {
			event.preventDefault();
			select(next);
			document.getElementById(`tab-${next}`)?.focus();
		}
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

		<div class="tabs" role="tablist" aria-label={t('dev.tabs')} tabindex="-1" onkeydown={keys}>
			{#each TABS as name (name)}
				<button type="button" role="tab" id="tab-{name}" aria-selected={tab === name} aria-controls="panel" tabindex={tab === name ? 0 : -1}
					onclick={() => select(name)}>{t(`dev.tab.${name}` as MessageKey)}</button>
			{/each}
		</div>

		<div class="dev-tab" id="panel" role="tabpanel" aria-labelledby="tab-{tab}" aria-busy={loading}>
			{#if error}
				<p class="notice error" role="alert">{error}</p>
			{:else if !data}
				<p class="muted">{t('common.loading')}</p>
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
	.tabs {
		display: flex;
		gap: 2px;
		margin: 0 0 20px;
		border-bottom: 1px solid var(--rule-strong);
		overflow-x: auto;
		scrollbar-width: none;
	}
	.tabs button {
		border: 0;
		background: none;
		padding: 10px 14px;
		font: inherit;
		font-weight: 500;
		color: var(--ink-2);
		border-bottom: 2px solid transparent;
		margin-bottom: -1px;
		cursor: pointer;
		white-space: nowrap;
	}
	.tabs button:hover {
		color: var(--ink);
	}
	.tabs button[aria-selected='true'] {
		color: var(--ink);
		border-bottom-color: var(--graphite);
	}
	.tabs button:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: -2px;
		border-radius: 4px 4px 0 0;
	}
</style>
