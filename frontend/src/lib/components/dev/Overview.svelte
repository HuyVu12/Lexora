<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import Term from '#lib/components/Term.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDate } from '#lib/i18n/index.svelte.js';
	import { act, notify } from '#lib/toast.svelte.js';
	import type { DevOverview, Feature, FeatureControl } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	let { data, reload }: { data: DevOverview; reload: () => void } = $props();

	const FEATURES: Feature[] = ['chat', 'extraction', 'proposal', 'embedding'];
	const num = (v: number) => v.toLocaleString();
	const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
	let limits = $state<Record<string, string>>({});
	let saving = $state('');
	$effect(() => {
		limits = Object.fromEntries(FEATURES.map((f) => [f, data.controls[f].daily_limit === null ? '' : String(data.controls[f].daily_limit)]));
	});

	function alertText(a: DevOverview['alerts'][number]) {
		const feature = a.feature ? t(`dev.feature.${a.feature}` as MessageKey) : '';
		return t(`dev.alert.${a.code}` as MessageKey, { feature, used: a.used ?? 0, limit: a.limit ?? 0, value: a.code === 'error_rate' ? pct(a.value ?? 0) : (a.value ?? 0) });
	}

	async function save(feature: Feature, change: Partial<FeatureControl>) {
		const current = data.controls[feature];
		const raw = (limits[feature] ?? '').trim();
		const daily = change.daily_limit !== undefined ? change.daily_limit : raw === '' ? null : Number(raw);
		if (daily !== null && (!Number.isInteger(daily) || daily < 0)) {
			notify({ key: 'dev.controls.invalid' }, true);
			return;
		}
		saving = feature;
		const ok = await act(() => api('/api/dev/controls', { feature, enabled: change.enabled ?? current.enabled, daily_limit: daily }));
		saving = '';
		if (ok) {
			notify({ key: 'dev.controls.saved' });
			reload();
		}
	}

	function describe(change: DevOverview['changes'][number]) {
		try {
			const before = change.before ? JSON.parse(change.before) : {};
			const after = JSON.parse(change.after);
			if (change.key !== 'controls') return t('dev.change.notes');
			const parts = FEATURES.filter((f) => JSON.stringify(before[f]) !== JSON.stringify(after[f])).map((f) => {
				const c = after[f] as FeatureControl;
				return `${t(`dev.feature.${f}` as MessageKey)}: ${c.enabled ? t('dev.on') : t('dev.off')}, ${c.daily_limit === null ? t('dev.noLimit') : t('dev.limitN', { n: c.daily_limit })}`;
			});
			return parts.join('; ') || t('dev.change.controls');
		} catch {
			return change.key;
		}
	}
</script>

{#if data.alerts.length}
	<ul class="alerts" aria-label={t('dev.alerts')}>
		{#each data.alerts as a, i (i)}
			<li class="notice small" class:error={a.level === 'critical'} class:warn={a.level === 'warning'}><Icon name="warn" size={16} />{alertText(a)}</li>
		{/each}
	</ul>
{:else}
	<p class="notice info small"><Icon name="check" size={16} />{t('dev.alerts.none')}</p>
{/if}

<div class="dev-tiles">
	<div class="dev-tile"><span class="label">{t('dev.tile.calls')}</span><strong>{num(data.today.calls)}</strong><span class="small muted">{t('dev.tile.today')}</span></div>
	<div class="dev-tile" class:bad={data.today.calls > 0 && data.today.errors / data.today.calls > 0.2}>
		<span class="label">{t('dev.tile.errors')}</span><strong>{num(data.today.errors)}</strong>
		<span class="small muted">{data.today.calls ? pct(data.today.errors / data.today.calls) : '-'}</span>
	</div>
	<div class="dev-tile"><span class="label"><Term key="blocked_calls">{t('dev.tile.blocked')}</Term></span><strong>{num(data.today.blocked)}</strong><span class="small muted">{t('dev.tile.today')}</span></div>
	<div class="dev-tile"><span class="label">{t('dev.tile.tokens')}</span><strong>{num(data.today.prompt_tokens + data.today.completion_tokens)}</strong>
		<span class="small muted">{t('dev.tile.tokensSplit', { in: num(data.today.prompt_tokens), out: num(data.today.completion_tokens) })}</span></div>
	<div class="dev-tile"><span class="label">{t('dev.tile.cost')}</span><strong>{data.today.cost_usd ? `${data.today.cost_usd.toFixed(2)} USD` : '-'}</strong><span class="small muted">{t('dev.tile.costNote')}</span></div>
</div>

<section class="panel" aria-labelledby="controls-heading">
	<h2 class="heading" id="controls-heading">{t('dev.controls.title')}</h2>
	<p class="small muted">{data.can_change ? t('dev.controls.lead') : t('dev.controls.readOnly')}</p>
	<div class="table-scroll">
		<table class="table wide">
			<thead>
				<tr>
					<th scope="col">{t('dev.col.feature')}</th>
					<th scope="col">{t('dev.col.model')}</th>
					<th scope="col" class="num"><Term key="run_budget">{t('dev.col.runBudget')}</Term></th>
					<th scope="col" class="num">{t('dev.col.today')}</th>
					<th scope="col"><Term key="feature_switch">{t('dev.col.switch')}</Term></th>
					<th scope="col"><Term key="daily_limit">{t('dev.col.limit')}</Term></th>
				</tr>
			</thead>
			<tbody>
				{#each FEATURES as f (f)}
					{@const control = data.controls[f]}
					{@const model = data.models[f]}
					<tr>
						<th scope="row">{t(`dev.feature.${f}` as MessageKey)}<span class="small muted block">{t(`dev.feature.${f}.d` as MessageKey)}</span></th>
						<td>{#if model}<code>{model.model}</code><span class="small muted block">{model.provider}</span>{:else}<span class="muted">{t('dev.notEnabled')}</span>{/if}</td>
						<td class="num">{model && model.max_calls ? `${model.calls ?? 0}/${model.max_calls}` : '-'}</td>
						<td class="num">{data.today.by_feature[f]}{control.daily_limit !== null ? ` / ${control.daily_limit}` : ''}</td>
						<td>
							{#if data.can_change}
								<button type="button" class="switch" role="switch" aria-checked={control.enabled} disabled={saving === f}
									aria-label={t('dev.switchLabel', { feature: t(`dev.feature.${f}` as MessageKey) })}
									onclick={() => save(f, { enabled: !control.enabled })}><span></span>{control.enabled ? t('dev.on') : t('dev.off')}</button>
							{:else}
								<span class="chip" class:off={!control.enabled}>{control.enabled ? t('dev.on') : t('dev.off')}</span>
							{/if}
						</td>
						<td>
							{#if data.can_change}
								<form class="limit" onsubmit={(e) => { e.preventDefault(); save(f, {}); }}>
									<label class="visually-hidden" for="limit-{f}">{t('dev.limitFor', { feature: t(`dev.feature.${f}` as MessageKey) })}</label>
									<input id="limit-{f}" class="input" inputmode="numeric" placeholder={t('dev.noLimit')} bind:value={limits[f]} />
									<button type="submit" class="btn small" disabled={saving === f}>{t('dev.save')}</button>
								</form>
							{:else}
								{control.daily_limit === null ? t('dev.noLimit') : control.daily_limit}
							{/if}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</section>

<div class="dev-two">
	<section class="panel" aria-labelledby="running-heading">
		<h2 class="heading" id="running-heading">{t('dev.running.title')}</h2>
		{#if data.running.length}
			<ul class="dev-list">{#each data.running as d (d.id)}<li><a href="/drafts/{d.id}">{d.title}</a><span class="small muted">{d.kb_name}</span></li>{/each}</ul>
		{:else}
			<p class="small muted">{t('dev.running.none')}</p>
		{/if}
		<p class="small muted">{t('dev.startedAt', { at: formatDate(data.started_at) })}</p>
	</section>
	<section class="panel" aria-labelledby="changes-heading">
		<h2 class="heading" id="changes-heading">{t('dev.changes.title')}</h2>
		{#if data.changes.length}
			<ul class="dev-list">{#each data.changes as c, i (i)}<li><span>{describe(c)}</span><span class="small muted">@{c.actor} · {formatDate(c.at)}</span></li>{/each}</ul>
		{:else}
			<p class="small muted">{t('dev.changes.none')}</p>
		{/if}
	</section>
</div>

<style>
	.alerts {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 8px;
	}
	.notice {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.block {
		display: block;
	}
	.switch {
		display: inline-flex;
		align-items: center;
		gap: 8px;
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
		transition: background 0.15s var(--ease-out);
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
		transition: transform 0.15s var(--ease-out);
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
	.chip.off {
		color: var(--reject);
		border-color: currentColor;
	}
	.limit {
		display: flex;
		gap: 6px;
		align-items: center;
	}
	.limit .input {
		width: 9.5rem;
		min-width: 0;
	}
	@media (prefers-reduced-motion: reduce) {
		.switch span,
		.switch span::after {
			transition: none;
		}
	}
</style>
