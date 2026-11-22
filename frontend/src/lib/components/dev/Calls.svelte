<script lang="ts">
	import DailyBars from './DailyBars.svelte';
	import Term from '#lib/components/Term.svelte';
	import { t, formatDate } from '#lib/i18n/index.svelte.js';
	import type { DevCalls, Feature } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	let { data }: { data: DevCalls } = $props();

	const FEATURES: Feature[] = ['chat', 'extraction', 'proposal', 'embedding'];
	const num = (v: number) => v.toLocaleString();
	const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
	const seconds = (ms: number | null) => (ms === null ? '-' : ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`);
	const days = $derived(data.daily.map((d) => d.day));
	const sum = (pick: (f: { ok: number; error: number; blocked: number }) => number) =>
		data.daily.map((d) => FEATURES.reduce((total, f) => total + pick(d.features[f]), 0));
	const byStatus = $derived([
		{ key: 'ok', label: t('dev.status.ok'), color: 'var(--graphite)', values: sum((f) => f.ok) },
		{ key: 'error', label: t('dev.status.error'), color: 'var(--reject)', values: sum((f) => f.error) },
		{ key: 'blocked', label: t('dev.status.blocked'), color: 'var(--attention)', values: sum((f) => f.blocked) }
	]);
	const featureColors: Record<Feature, string> = { chat: 'var(--flag)', extraction: 'var(--graphite)', proposal: '#7a5bb5', embedding: 'var(--approve)' };
	const byFeature = $derived(FEATURES.map((f) => ({ key: f, label: t(`dev.feature.${f}` as MessageKey), color: featureColors[f],
		values: data.daily.map((d) => d.features[f].ok + d.features[f].error) })));
	const error = (code: string) => t(`results.error.${code}` as MessageKey) ?? t(`dev.code.${code}` as MessageKey) ?? code;
	// Charts only when the range has a call to show; an empty range is one quiet line.
	const any = $derived(data.daily.some((d) => FEATURES.some((f) => d.features[f].ok + d.features[f].error + d.features[f].blocked > 0)));
	const RECENT = 10;
	let allRecent = $state(false);
	const recent = $derived(allRecent ? data.recent : data.recent.slice(0, RECENT));
</script>

{#if any}
<div class="dev-two">
	<section class="panel" aria-labelledby="status-chart">
		<h2 class="heading" id="status-chart">{t('dev.calls.byStatus')}</h2>
		<DailyBars {days} series={byStatus} label={t('dev.calls.byStatus')} />
	</section>
	<section class="panel" aria-labelledby="feature-chart">
		<h2 class="heading" id="feature-chart">{t('dev.calls.byFeature')}</h2>
		<DailyBars {days} series={byFeature} label={t('dev.calls.byFeature')} />
	</section>
</div>
{/if}

{#if data.models.length}
<section class="panel" aria-labelledby="models-heading">
	<h2 class="heading" id="models-heading">{t('dev.calls.models')}</h2>
		<div class="table-scroll">
			<table class="table wide">
				<thead>
					<tr>
						<th scope="col">{t('dev.col.model')}</th>
						<th scope="col">{t('dev.col.feature')}</th>
						<th scope="col" class="num">{t('dev.col.calls')}</th>
						<th scope="col" class="num">{t('dev.col.errorRate')}</th>
						<th scope="col" class="num">{t('dev.col.tokensIn')}</th>
						<th scope="col" class="num">{t('dev.col.tokensOut')}</th>
						<th scope="col" class="num">{t('dev.col.reasoning')}</th>
						<th scope="col" class="num">{t('dev.col.p50')}</th>
						<th scope="col" class="num"><Term key="latency_p95">p95</Term></th>
						<th scope="col" class="num">{t('dev.col.cost')}</th>
					</tr>
				</thead>
				<tbody>
					{#each data.models as m (m.feature + m.model)}
						<tr>
							<th scope="row"><code>{m.model}</code> <span class="small muted">{m.provider}</span></th>
							<td>{t(`dev.feature.${m.feature}` as MessageKey)}</td>
							<td class="num">{num(m.calls)}</td>
							<td class="num" class:status-error={m.error_rate > 0.2}>{pct(m.error_rate)}</td>
							<td class="num">{num(m.prompt_tokens)}</td>
							<td class="num">{num(m.completion_tokens)}</td>
							<td class="num">{m.reasoning_tokens ? num(m.reasoning_tokens) : '-'}</td>
							<td class="num">{seconds(m.p50_ms)}</td>
							<td class="num">{seconds(m.p95_ms)}</td>
							<td class="num">{m.cost_usd ? `${m.cost_usd.toFixed(2)} USD` : '-'}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
</section>
{/if}

{#if Object.keys(data.codes).length}
	<section class="panel" aria-labelledby="codes-heading">
		<h2 class="heading" id="codes-heading">{t('dev.calls.codes')}</h2>
		<ul class="dev-list codes">{#each Object.entries(data.codes) as [code, n] (code)}<li><span>{error(code)}{#if error(code) !== code} <code class="small">{code}</code>{/if}</span><strong>{n}</strong></li>{/each}</ul>
	</section>
{/if}

<section class="panel" aria-labelledby="recent-heading">
	<h2 class="heading" id="recent-heading">{t('dev.calls.recent')}</h2>
	<p class="small muted">{t('dev.calls.privacy')}</p>
	{#if !any}<p class="dev-empty">{t('dev.calls.none', { days: data.days })}</p>{/if}
	{#if data.recent.length}
		<div class="table-scroll">
			<table class="table wide">
				<thead>
					<tr>
						<th scope="col">{t('dev.col.time')}</th>
						<th scope="col">{t('dev.col.feature')}</th>
						<th scope="col">{t('dev.col.model')}</th>
						<th scope="col">{t('dev.col.actor')}</th>
						<th scope="col">{t('dev.col.status')}</th>
						<th scope="col" class="num">{t('dev.col.tokens')}</th>
						<th scope="col" class="num">{t('dev.col.duration')}</th>
					</tr>
				</thead>
				<tbody>
					{#each recent as c, i (i)}
						<tr>
							<td class="nowrap">{formatDate(c.at)}</td>
							<td>{t(`dev.feature.${c.feature}` as MessageKey)}{#if c.purpose}<span class="small muted block">{c.purpose}</span>{/if}</td>
							<td><code>{c.model}</code></td>
							<td>{c.actor ? `@${c.actor}` : '-'}</td>
							<td class="status-{c.status}">{t(`dev.status.${c.status}` as MessageKey)}{#if c.code}<span class="small block">{error(c.code)}</span>{/if}</td>
							<td class="num">{num(c.prompt_tokens)} / {num(c.completion_tokens)}</td>
							<td class="num">{seconds(c.duration_ms)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		{#if data.recent.length > RECENT}
			<div><button type="button" class="btn quiet small" aria-expanded={allRecent} onclick={() => (allRecent = !allRecent)}>{allRecent ? t('dev.calls.recentFewer', { n: RECENT }) : t('dev.calls.recentMore', { n: data.recent.length })}</button></div>
		{/if}
	{:else if any}
		<p class="dev-empty">{t('dev.calls.noneYet')}</p>
	{/if}
</section>

<style>
	.block {
		display: block;
	}
	.nowrap {
		white-space: nowrap;
	}
	.codes {
		grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
		gap: 8px 32px;
	}
	p {
		margin: 0;
	}
</style>
