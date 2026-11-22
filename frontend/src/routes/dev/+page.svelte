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
	import '#lib/components/dev/dev.css';
	import { api } from '#lib/api.js';
	import { t, i18n } from '#lib/i18n/index.svelte.js';
	import { session, canMonitor } from '#lib/session.svelte.js';
	import type { MessageKey } from '#lib/i18n/vi.js';
	import type { DevCalls, DevExperiments, DevKb, DevOverview, DevReport, DevUsage } from '#lib/types.js';

	// Operations first (status, model calls, usage, knowledge bases), then the research tabs. The system details
	// live at the foot of the overview; an old #system link opens them there.
	const TABS = ['overview', 'calls', 'usage', 'kb', 'experiments', 'report'] as const;
	type Tab = (typeof TABS)[number];
	const ENDPOINT: Record<Tab, string> = {
		overview: '/api/dev/overview',
		calls: '/api/dev/calls',
		usage: '/api/dev/usage',
		kb: '/api/dev/kb',
		experiments: '/api/dev/experiments',
		report: '/api/dev/report'
	};
	const RANGED: Tab[] = ['calls', 'usage'];
	// Tabs whose numbers move by the minute refresh themselves while the page is visible.
	const LIVE: Tab[] = ['overview', 'calls', 'usage'];
	const EVERY = 60_000;

	let tab = $state<Tab>('overview');
	let showSystem = $state(false);
	let days = $state(14);
	// Each tab keeps the last numbers it loaded (per range), so coming back to a tab shows them at once while
	// a fresh copy loads. The data always travels with the tab that loaded it: a tab never renders another's.
	let loaded = $state<Record<string, unknown>>({});
	let loadedAt = $state<Record<string, number>>({});
	const slot = (which: Tab) => (RANGED.includes(which) ? `${which}:${days}` : which);
	const data = $derived(loaded[slot(tab)] ?? null);
	const overview = $derived((loaded.overview as DevOverview | undefined) ?? null);
	const alerts = $derived(overview?.alerts ?? []);
	const critical = $derived(alerts.some((a) => a.level === 'critical'));
	const updated = $derived(loadedAt[slot(tab)] ? new Date(loadedAt[slot(tab)]).toLocaleTimeString(i18n.locale === 'vi' ? 'vi-VN' : 'en-GB', { hour: '2-digit', minute: '2-digit' }) : '');
	let error = $state('');
	let loading = $state(false);
	let request = 0;

	function fromHash() {
		const name = location.hash.slice(1);
		showSystem = name === 'system';
		tab = TABS.includes(name as Tab) ? (name as Tab) : 'overview';
	}
	$effect(() => {
		fromHash();
		addEventListener('hashchange', fromHash);
		return () => removeEventListener('hashchange', fromHash);
	});

	async function load(which: Tab = tab) {
		const mine = ++request;
		loading = true;
		error = '';
		try {
			const value = await api(ENDPOINT[which] + (RANGED.includes(which) ? `?days=${days}` : ''));
			if (mine === request) {
				loaded[slot(which)] = value;
				loadedAt[slot(which)] = Date.now();
			}
		} catch (e) {
			if (mine === request) error = (e as Error).message;
		} finally {
			if (mine === request) loading = false;
		}
	}
	$effect(() => {
		void tab;
		void days;
		if (canMonitor(session.account)) load(tab);
	});
	// The health line reads the overview's alerts on every tab; fetch them once when another tab opens first.
	$effect(() => {
		if (canMonitor(session.account) && tab !== 'overview' && !loaded.overview)
			api(ENDPOINT.overview).then((value) => {
				if (!loaded.overview) loaded.overview = value;
			}, () => {});
	});
	$effect(() => {
		if (!LIVE.includes(tab) || !canMonitor(session.account)) return;
		const timer = setInterval(() => {
			if (document.visibilityState === 'visible' && !loading) load(tab);
		}, EVERY);
		return () => clearInterval(timer);
	});

	function select(next: Tab) {
		history.replaceState(history.state, '', `#${next}`);
		showSystem = false;
	}
	function toOverview() {
		tab = 'overview';
		select('overview');
		requestAnimationFrame(() => document.getElementById('alerts-heading')?.closest('section')?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }));
	}
</script>

<svelte:head><title>{t('dev.title')} · Lexora</title></svelte:head>

<div class="page">
	{#if !canMonitor(session.account)}
		<h1 class="title">{t('common.forbidden.title')}</h1>
		<p class="lead">{t('common.forbidden.body')}</p>
	{:else}
		<header class="page-head dev-head">
			<div>
				<h1 class="title">{t('dev.title')}</h1>
			</div>
			<div class="head-tools">
				{#if RANGED.includes(tab)}
					<div class="segmented" role="group" aria-label={t('dev.range')}>
						{#each [7, 14, 30] as n (n)}<button type="button" aria-pressed={days === n} onclick={() => (days = n)}>{t('dev.days', { n })}</button>{/each}
					</div>
				{/if}
				<div class="health">
					{#if overview}
						<button type="button" class="health-pill" class:ok={!alerts.length} class:warn={alerts.length && !critical} class:bad={critical} data-tour="dev-alerts" onclick={toOverview}>
							<i aria-hidden="true"></i>{alerts.length ? t('dev.health.alerts', { n: alerts.length }) : t('dev.health.ok')}
						</button>
					{/if}
					{#if updated}<span class="small muted updated" title={LIVE.includes(tab) ? t('dev.health.auto') : undefined}>{t('dev.health.updated', { time: updated })}</span>{/if}
					<button type="button" class="btn quiet icon-only" class:spinning={loading} onclick={() => load()} disabled={loading} aria-label={t('dev.refresh')} title={t('dev.refresh')}>
						<Icon name="history" size={16} />
					</button>
				</div>
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
					{#each [0, 1, 2, 3] as i (i)}<div class="dev-tile ghost"><Skeleton width="58%" height="12px" /><span class="ghost-main"><Skeleton width="34%" height="24px" />{#if tab === 'overview'}<Skeleton width="96px" height="24px" />{/if}</span><Skeleton width="44%" height="11px" /></div>{/each}
				</div>
				<div class="panel ghost-panel" aria-hidden="true">
					<Skeleton width="26%" height="16px" />
					<Skeleton width="52%" height="11px" />
					{#each [0, 1, 2, 3] as i (i)}<span class="ghost-row"><Skeleton width="70%" height="12px" /><Skeleton width="46%" height="18px" radius="999px" /><Skeleton width="60%" height="12px" /><Skeleton width="50%" height="12px" /></span>{/each}
				</div>
			{:else if tab === 'overview'}
				<Overview data={data as DevOverview} reload={() => load('overview')} {showSystem} />
			{:else if tab === 'calls'}
				<Calls data={data as DevCalls} />
			{:else if tab === 'experiments'}
				<Experiments data={data as DevExperiments} />
			{:else if tab === 'report'}
				<Report data={data as DevReport} reload={() => load('report')} />
			{:else if tab === 'usage'}
				<Usage data={data as DevUsage} />
			{:else}
				<KbStats data={data as DevKb} />
			{/if}
		</div>
	{/if}
</div>

<style>
	.page :global(.tabs) {
		margin-bottom: var(--space-5);
	}
	/* Same height on every tab (with or without the range control), so the title never jumps. */
	.head-tools {
		display: flex;
		flex-wrap: wrap;
		min-height: 40px;
		align-items: center;
		justify-content: flex-end;
		gap: 8px 16px;
	}
	.health {
		display: flex;
		align-items: center;
		gap: 10px;
	}
	.health-pill {
		display: inline-flex;
		align-items: center;
		gap: 7px;
		min-height: 30px;
		padding: 3px 12px 3px 10px;
		border-radius: 999px;
		border: 1px solid var(--rule);
		background: var(--paper);
		font: inherit;
		font-size: 13.5px;
		font-weight: 500;
		color: var(--ink-2);
		cursor: pointer;
		white-space: nowrap;
		transition:
			border-color var(--dur-fast) ease,
			transform var(--dur-fast) var(--ease-out);
	}
	.health-pill:active {
		transform: scale(0.97);
		transition-duration: var(--dur-press);
	}
	@media (hover: hover) {
		.health-pill:hover {
			border-color: var(--rule-strong);
		}
	}
	.health-pill i {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--approve);
	}
	.health-pill.warn {
		background: var(--attention-soft);
		border-color: #f0d3a1;
		color: var(--attention);
	}
	.health-pill.warn i {
		background: #c47d0e;
	}
	.health-pill.bad {
		background: var(--reject-soft);
		border-color: #f1c4bf;
		color: var(--reject);
	}
	.health-pill.bad i {
		background: var(--reject);
	}
	.health-pill:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	.updated {
		white-space: nowrap;
		font-variant-numeric: tabular-nums;
	}
	.icon-only {
		width: 34px;
		height: 34px;
		min-height: 34px;
		padding: 0;
		justify-content: center;
	}
	.icon-only.spinning :global(svg) {
		animation: turn 0.9s linear infinite;
	}
	@keyframes turn {
		to {
			transform: rotate(-360deg);
		}
	}
	.ghost {
		gap: 10px;
	}
	.ghost-main {
		display: flex;
		justify-content: space-between;
		align-items: flex-end;
		gap: 12px;
	}
	.ghost-panel {
		display: grid;
		gap: 14px;
	}
	.ghost-row {
		display: grid;
		grid-template-columns: 2fr 2fr 1.5fr 1fr;
		gap: 16px;
		align-items: center;
		height: 52px;
		border-top: 1px solid var(--rule);
	}
	@media (max-width: 700px) {
		.dev-head {
			grid-template-columns: minmax(0, 1fr);
			align-items: start;
			gap: var(--space-3);
		}
		.head-tools {
			justify-content: space-between;
		}
		.ghost-row {
			grid-template-columns: 1fr 1fr;
			height: auto;
			padding: 12px 0;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.icon-only.spinning :global(svg) {
			animation: none;
		}
		.health-pill {
			transition: none;
		}
	}
</style>
