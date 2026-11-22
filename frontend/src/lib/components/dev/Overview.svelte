<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import Term from '#lib/components/Term.svelte';
	import Skeleton from '#lib/components/Skeleton.svelte';
	import Sparkline from './Sparkline.svelte';
	import Meter from './Meter.svelte';
	import System from './System.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDate } from '#lib/i18n/index.svelte.js';
	import { act, notify } from '#lib/toast.svelte.js';
	import type { DevOverview, DevSystem, Feature, FeatureControl } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';
	import { countUp, revealItems, rise } from '#lib/motion.js';

	let { data, reload, showSystem = false }: { data: DevOverview; reload: () => void; showSystem?: boolean } = $props();

	const FEATURES: Feature[] = ['chat', 'extraction', 'proposal', 'embedding'];
	const num = (v: number) => v.toLocaleString();
	const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
	const featureName = (f: Feature) => t(`dev.feature.${f}` as MessageKey);

	// Today against the days before it: the trend arrives oldest first with today last.
	const days = $derived(data.trend.map((d) => d.day));
	const series = (pick: (d: DevOverview['trend'][number]) => number) => data.trend.map(pick);
	const week = (values: number[]) => values.slice(-7).reduce((a, b) => a + b, 0);
	const calls = $derived(series((d) => d.calls));
	const questions = $derived(series((d) => d.questions));
	const problems = $derived(series((d) => d.errors + d.blocked));
	const tokenSeries = $derived(series((d) => d.tokens));
	const todayQuestions = $derived(questions.at(-1) ?? 0);
	// A week without a single model call or question says so in one line instead of four tiles of zeros.
	const quiet = $derived(week(calls) + week(questions) + week(problems) === 0);
	const errorShare = $derived(data.today.calls ? data.today.errors / data.today.calls : 0);
	const problemTone = $derived(data.today.calls >= 5 && errorShare > 0.2 ? 'bad' : data.today.errors + data.today.blocked > 0 ? 'warn' : 'accent');
	const spark = (label: string, values: number[]) => t('dev.kpi.spark', { label, total: num(values.reduce((a, b) => a + b, 0)), max: num(Math.max(0, ...values)) });

	type State = 'running' | 'off' | 'limit' | 'idle';
	function stateOf(f: Feature): State {
		const control = data.controls[f];
		if (!data.models[f]) return 'idle';
		if (!control.enabled) return 'off';
		if (control.daily_limit !== null && data.today.by_feature[f] >= control.daily_limit) return 'limit';
		return 'running';
	}
	const idle = $derived(FEATURES.every((f) => !data.models[f]));

	function alertText(a: DevOverview['alerts'][number]) {
		const feature = a.feature ? featureName(a.feature) : '';
		return t(`dev.alert.${a.code}` as MessageKey, { feature, used: a.used ?? 0, limit: a.limit ?? 0, value: a.code === 'error_rate' ? pct(a.value ?? 0) : (a.value ?? 0) });
	}

	// Limits are edited one feature at a time; a refresh in the background never touches what is being typed.
	let editing = $state<Feature | null>(null);
	let draft = $state('');
	let saving = $state('');
	function edit(f: Feature) {
		editing = f;
		draft = data.controls[f].daily_limit === null ? '' : String(data.controls[f].daily_limit);
	}
	async function save(f: Feature, change: Partial<FeatureControl>) {
		const current = data.controls[f];
		let daily = current.daily_limit;
		if (change.daily_limit !== undefined) daily = change.daily_limit;
		else if (editing === f) daily = draft.trim() === '' ? null : Number(draft.trim());
		if (daily !== null && (!Number.isInteger(daily) || daily < 0)) {
			notify({ key: 'dev.controls.invalid' }, true);
			return;
		}
		saving = f;
		const ok = await act(() => api('/api/dev/controls', { feature: f, enabled: change.enabled ?? current.enabled, daily_limit: daily }));
		saving = '';
		if (ok) {
			if (editing === f) editing = null;
			notify({ key: 'dev.controls.saved' });
			reload();
		}
	}
	const focus = (node: HTMLInputElement) => {
		node.focus();
		node.select();
	};

	// A change lists only the features it touched; the very first change compares with the defaults (on, no limit).
	function describe(change: DevOverview['changes'][number]) {
		try {
			if (change.key !== 'controls') return t('dev.change.notes');
			const before = change.before ? JSON.parse(change.before) : {};
			const after = JSON.parse(change.after);
			const same = (a?: FeatureControl, b?: FeatureControl) => (a?.enabled ?? true) === (b?.enabled ?? true) && (a?.daily_limit ?? null) === (b?.daily_limit ?? null);
			const parts = FEATURES.filter((f) => !same(before[f], after[f])).map((f) => {
				const c = after[f] as FeatureControl;
				return `${featureName(f)}: ${c.enabled ? t('dev.on') : t('dev.off')}, ${c.daily_limit === null ? t('dev.noLimit') : t('dev.limitN', { n: c.daily_limit })}`;
			});
			return parts.join('; ') || t('dev.change.controls');
		} catch {
			return change.key;
		}
	}
	const CHANGES = 4;
	let allChanges = $state(false);
	const changes = $derived(allChanges ? data.changes : data.changes.slice(0, CHANGES));

	// The system details are a click away instead of a tab of their own; they load the first time they open.
	let systemOpen = $state(false);
	let system = $state<DevSystem | null>(null);
	let systemError = $state('');
	$effect(() => {
		if (showSystem) systemOpen = true;
	});
	$effect(() => {
		if (systemOpen && !system) {
			api('/api/dev/system').then(
				(value) => (system = value as DevSystem),
				(e) => (systemError = (e as Error).message)
			);
		}
	});
</script>

{#if data.alerts.length}
	<section class="panel alerts" class:critical={data.alerts.some((a) => a.level === 'critical')} aria-labelledby="alerts-heading">
		<h2 class="heading" id="alerts-heading">{t('dev.alerts.title')}</h2>
		<ul {@attach revealItems({ step: 40, y: 6 })}>
			{#each data.alerts as a, i (i)}
				<li class={a.level}><Icon name="warn" size={16} /><span>{alertText(a)}</span></li>
			{/each}
		</ul>
	</section>
{/if}

{#if quiet}
	<p class="quiet-line"><Icon name="info" size={16} />{t('dev.kpi.quiet')}</p>
{:else}
	<div class="kpis" {@attach revealItems({ step: 45 })}>
		<div class="kpi">
			<span class="label">{t('dev.kpi.calls')}</span>
			<div class="kpi-main">
				<strong class:zero={!data.today.calls} {@attach countUp(data.today.calls, { format: num })}></strong>
				<Sparkline {days} values={calls} label={spark(t('dev.kpi.calls'), calls)} />
			</div>
			<span class="small muted">{t('dev.kpi.week', { n: num(week(calls)) })}</span>
		</div>
		<div class="kpi">
			<span class="label">{t('dev.kpi.questions')}</span>
			<div class="kpi-main">
				<strong class:zero={!todayQuestions} {@attach countUp(todayQuestions, { format: num })}></strong>
				<Sparkline {days} values={questions} label={spark(t('dev.kpi.questions'), questions)} />
			</div>
			<span class="small muted">{t('dev.kpi.week', { n: num(week(questions)) })}</span>
		</div>
		<div class="kpi" class:bad={problemTone === 'bad'}>
			<span class="label">{t('dev.kpi.errors')}</span>
			<div class="kpi-main">
				<strong class:zero={!data.today.errors} {@attach countUp(data.today.errors, { format: num })}></strong>
				<Sparkline {days} values={problems} tone={problemTone} label={spark(t('dev.kpi.errors'), problems)} />
			</div>
			<span class="small muted">
				{data.today.calls ? t('dev.kpi.errorRate', { rate: pct(errorShare) }) : t('dev.kpi.noCalls')} ·
				<Term key="blocked_calls">{t('dev.kpi.blocked', { n: num(data.today.blocked) })}</Term>
			</span>
		</div>
		<div class="kpi">
			<span class="label">{t('dev.kpi.tokens')}</span>
			<div class="kpi-main">
				<strong class:zero={!tokenSeries.at(-1)} {@attach countUp(tokenSeries.at(-1) ?? 0, { format: num })}></strong>
				<Sparkline {days} values={tokenSeries} label={spark(t('dev.kpi.tokens'), tokenSeries)} />
			</div>
			<span class="small muted">{data.today.cost_usd ? t('dev.kpi.cost', { cost: data.today.cost_usd.toFixed(2) }) : t('dev.kpi.week', { n: num(week(tokenSeries)) })}</span>
		</div>
	</div>
{/if}

<section class="panel features" data-tour="dev-controls" aria-labelledby="features-heading">
	<div class="features-head">
		<h2 class="heading" id="features-heading">{t('dev.features.title')}</h2>
		<p class="small muted">{data.can_change ? t('dev.features.leadDev') : t('dev.features.leadAdmin')}</p>
		{#if idle}<p class="small">{t('dev.features.idle')}</p>{/if}
	</div>
	<ul class="feature-list" class:compact={idle} {@attach revealItems({ step: 40, y: 6, delay: 60 })}>
		{#each FEATURES as f (f)}
			{@const control = data.controls[f]}
			{@const model = data.models[f]}
			{@const used = data.today.by_feature[f]}
			{@const status = stateOf(f)}
			<li class="feature" class:idle={status === 'idle'}>
				<div class="who">
					<span class="name">{featureName(f)}</span>
					<span class="small muted">{t(`dev.feature.${f}.d` as MessageKey)}</span>
				</div>
				{#if !idle}
				<div class="status">
					<span class="pill {status}"><i aria-hidden="true"></i>{t(`dev.state.${status}` as MessageKey)}</span>
					{#if model}<span class="model"><code>{model.model}</code> <span class="small muted">{model.provider}</span></span>{/if}
				</div>
				{/if}
				{#if model || used}
				<div class="use">
						{#if control.daily_limit !== null}
							<span class="small">{t('dev.use.todayOf', { used: num(used), limit: num(control.daily_limit) })}</span>
							<Meter {used} limit={control.daily_limit} label={t('dev.limitFor', { feature: featureName(f) })} />
						{:else}
							<span class="small">{t('dev.use.today', { n: used })}</span>
						{/if}
						{#if model?.max_calls}
							<span class="small muted run"><Term key="run_budget">{t('dev.use.run', { used: model.calls ?? 0, max: model.max_calls })}</Term></span>
							<Meter used={model.calls ?? 0} limit={model.max_calls} label={t('dev.col.runBudget')} />
						{/if}
				</div>
				{:else if !idle}<div class="use"></div>{/if}
				<div class="controls">
					{#if data.can_change}
						<button type="button" class="switch" role="switch" aria-checked={control.enabled} disabled={saving === f}
							aria-label={t('dev.switchLabel', { feature: featureName(f) })}
							onclick={() => save(f, { enabled: !control.enabled })}><span></span>{control.enabled ? t('dev.on') : t('dev.off')}</button>
						{#if editing === f}
							<form class="limit" onsubmit={(e) => { e.preventDefault(); save(f, {}); }}>
								<label class="visually-hidden" for="limit-{f}">{t('dev.limitFor', { feature: featureName(f) })}</label>
								<input id="limit-{f}" class="input" inputmode="numeric" placeholder={t('dev.noLimit')} bind:value={draft} {@attach focus} onkeydown={(e) => { if (e.key === 'Escape') editing = null; }} />
								<button type="submit" class="btn small primary" disabled={saving === f}>{t('dev.save')}</button>
								<button type="button" class="btn small quiet" onclick={() => (editing = null)}>{t('dev.cancel')}</button>
							</form>
						{:else}
							<button type="button" class="btn small quiet limit-btn" aria-label={t('dev.limitEdit', { feature: featureName(f) })} onclick={() => edit(f)}>
								<Icon name="edit" size={14} />{control.daily_limit === null ? t('dev.noLimit') : t('dev.limitN', { n: control.daily_limit })}
							</button>
						{/if}
					{:else if !control.enabled || control.daily_limit !== null}
						<span class="small">{!control.enabled ? t('dev.switchedOff') : t('dev.limitN', { n: control.daily_limit ?? 0 })}</span>
					{/if}
				</div>
			</li>
		{/each}
	</ul>
</section>

{#if data.running.length || data.changes.length}
	<div class="activity" class:pair={data.running.length && data.changes.length}>
		{#if data.running.length}
			<section class="panel" aria-labelledby="running-heading">
				<h2 class="heading" id="running-heading">{t('dev.running.title')}</h2>
				<ul class="dev-list">{#each data.running as d (d.id)}<li><a href="/drafts/{d.id}">{d.title}</a><span class="small muted">{d.kb_name}</span></li>{/each}</ul>
			</section>
		{/if}
		{#if data.changes.length}
			<section class="panel" aria-labelledby="changes-heading">
				<h2 class="heading" id="changes-heading">{t('dev.changes.title')}</h2>
				<ul class="dev-list changes">{#each changes as c, i (i)}<li><span>{describe(c)}</span><span class="small muted">@{c.actor} · {formatDate(c.at)}</span></li>{/each}</ul>
				{#if data.changes.length > CHANGES}
					<div><button type="button" class="btn quiet small" aria-expanded={allChanges} onclick={() => (allChanges = !allChanges)}>{allChanges ? t('dev.changes.fewer') : t('dev.changes.more', { n: data.changes.length })}</button></div>
				{/if}
			</section>
		{/if}
	</div>
{/if}

<footer class="foot">
	<p class="small muted">
		{#if !data.running.length}{t('dev.running.none')}{/if}
		{#if !data.changes.length}{t('dev.changes.none')}{/if}
		{t('dev.startedAt', { at: formatDate(data.started_at) })}
	</p>
	<button type="button" class="btn quiet small sys-toggle" aria-expanded={systemOpen} aria-controls="system-details" onclick={() => (systemOpen = !systemOpen)}>
		{t('dev.sys.toggle')}<Icon name="chevron" size={14} />
	</button>
</footer>
{#if systemOpen}
	<div id="system-details" class="system" transition:rise={{ y: 6 }}>
		{#if systemError}
			<p class="notice error small" role="alert">{systemError}</p>
		{:else if system}
			<System data={system} />
		{:else}
			<div class="panel ghost" aria-hidden="true"><Skeleton width="30%" height="14px" /><Skeleton lines={4} height="12px" /></div>
		{/if}
	</div>
{/if}

<style>
	/* Alerts: one panel with a row per alert, coloured by level, instead of a stack of full-width banners. */
	.alerts ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0;
	}
	.alerts {
		gap: 4px;
		border-color: #f0d3a1;
	}
	.alerts.critical {
		border-color: #f1c4bf;
	}
	.alerts li {
		display: flex;
		gap: 10px;
		align-items: flex-start;
		padding: 8px 0;
		font-size: 14px;
		color: var(--ink);
	}
	.alerts li + li {
		border-top: 1px solid var(--rule);
	}
	.alerts li :global(svg) {
		flex: none;
		margin-top: 2px;
		color: var(--attention);
	}
	.alerts li.critical :global(svg) {
		color: var(--reject);
	}
	.quiet-line {
		display: flex;
		align-items: center;
		gap: 8px;
		margin: 0;
		padding: 2px 2px;
		font-size: 14px;
		color: var(--muted);
	}

	/* KPI strip: today's figure, a 14-day column sparkline, the last seven days underneath. */
	.kpis {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 12px;
	}
	.kpi {
		display: grid;
		align-content: start;
		gap: 4px;
		padding: 12px 14px;
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: var(--r-panel);
		min-width: 0;
	}
	.kpi.bad {
		background: var(--reject-soft);
		border-color: #f1c4bf;
	}
	.kpi-main {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		gap: 12px;
	}
	.kpi strong {
		font: 600 24px/1.1 var(--serif);
		font-variant-numeric: tabular-nums;
	}
	.kpi strong.zero {
		color: var(--muted);
		font-weight: 500;
	}
	.kpi.bad strong:not(.zero) {
		color: var(--reject);
	}
	.kpi .small {
		overflow-wrap: anywhere;
	}

	/* Features: one row each, status first; the controls sit at the end of the row. */
	.features-head {
		display: grid;
		gap: 4px;
	}
	.features-head p {
		margin: 0;
	}
	.feature-list {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.feature {
		display: grid;
		grid-template-columns: minmax(180px, 1.3fr) minmax(200px, 1.4fr) minmax(170px, 1.1fr) minmax(250px, auto);
		gap: 6px 20px;
		align-items: center;
		padding: 12px 0;
		border-top: 1px solid var(--rule);
	}
	.who,
	.status,
	.use {
		display: grid;
		gap: 3px;
		min-width: 0;
	}
	.name {
		font-weight: 500;
		font-size: 14.5px;
	}
	/* Nothing is on in this run: the list folds into two columns of name and controls, no repeated status. */
	.compact {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		column-gap: 32px;
	}
	.compact .feature {
		grid-template-columns: minmax(0, 1fr) auto;
		padding: 10px 0;
	}
	.status {
		justify-items: start;
	}
	.model {
		overflow-wrap: anywhere;
		font-size: 13px;
	}
	.pill {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 1px 9px 1px 8px;
		border-radius: 999px;
		font-size: 12.5px;
		font-weight: 500;
		white-space: nowrap;
		border: 1px solid transparent;
	}
	.pill i {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: currentColor;
	}
	.pill.running {
		color: var(--approve);
		background: var(--approve-soft);
	}
	.pill.off,
	.pill.limit {
		color: var(--reject);
		background: var(--reject-soft);
	}
	.pill.idle {
		color: var(--muted);
		border-color: var(--rule);
	}
	.pill.idle i {
		background: transparent;
		border: 1.5px solid currentColor;
		width: 6px;
		height: 6px;
	}
	.use .run {
		margin-top: 4px;
	}
	.controls {
		display: grid;
		grid-template-columns: 4.75rem minmax(10rem, auto);
		align-items: center;
		justify-content: end;
		gap: 10px;
		min-height: 32px;
	}
	.controls:empty {
		display: none;
	}
	.controls:has(> :only-child) {
		grid-template-columns: auto;
	}
	.limit-btn {
		color: var(--ink-2);
		gap: 6px;
		justify-content: flex-start;
	}
	.limit {
		display: flex;
		gap: 6px;
		align-items: center;
	}
	.limit .input {
		width: 9.5rem;
		min-width: 0;
		min-height: 32px;
		padding-block: 4px;
	}
	.switch {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		min-width: 4.5rem;
		border: 0;
		background: none;
		padding: 2px 0;
		font: inherit;
		font-size: 13.5px;
		color: var(--ink-2);
		cursor: pointer;
	}
	.switch span {
		position: relative;
		width: 34px;
		height: 20px;
		border-radius: 999px;
		background: var(--rule-strong);
		transition: background-color var(--dur-fast) var(--ease-out);
	}
	.switch span::after {
		content: '';
		position: absolute;
		top: 3px;
		left: 3px;
		width: 14px;
		height: 14px;
		border-radius: 50%;
		background: var(--paper);
		box-shadow: 0 1px 2px rgb(20 22 24 / 0.2);
		transition: transform var(--dur-fast) var(--ease-out);
	}
	.switch:active:not(:disabled) span::after {
		transform: scaleX(1.15);
	}
	.switch[aria-checked='true'] span {
		background: var(--approve);
	}
	.switch[aria-checked='true'] span::after {
		transform: translateX(14px);
	}
	.switch:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
		border-radius: 4px;
	}

	.activity {
		display: grid;
		gap: 16px;
		align-items: start;
	}
	.activity.pair {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
	.changes li > :first-child {
		color: var(--ink-2);
	}
	.foot {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 4px 12px;
		padding: 0 2px;
	}
	.foot p {
		margin: 0;
	}
	.sys-toggle {
		gap: 6px;
		color: var(--muted);
	}
	.sys-toggle :global(svg) {
		transition: transform var(--dur-fast) var(--ease-out);
	}
	.sys-toggle[aria-expanded='true'] :global(svg) {
		transform: rotate(180deg);
	}
	.system .ghost {
		display: grid;
		gap: 12px;
	}

	@media (max-width: 1100px) {
		.feature {
			grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		}
		.controls {
			justify-content: start;
		}
	}
	@media (max-width: 860px) {
		.compact {
			grid-template-columns: minmax(0, 1fr);
		}
		.kpis {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
		.activity.pair {
			grid-template-columns: 1fr;
		}
	}
	@media (max-width: 560px) {
		.kpis {
			gap: 8px;
		}
		.kpi {
			padding: 10px 12px;
		}
		.kpi-main {
			flex-direction: column;
			align-items: flex-start;
			gap: 6px;
		}
		.kpi-main :global(svg) {
			width: 100%;
		}
		.feature {
			grid-template-columns: minmax(0, 1fr);
			gap: 8px;
		}
		.use:empty {
			display: none;
		}
		.controls {
			justify-content: start;
		}
		.compact .feature {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.switch span,
		.switch span::after,
		.sys-toggle :global(svg) {
			transition: none;
		}
	}
</style>
