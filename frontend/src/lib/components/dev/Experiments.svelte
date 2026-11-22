<script lang="ts">
	import { t, formatDate } from '#lib/i18n/index.svelte.js';
	import type { DevExperiments } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';
	import { countUp, revealItems } from '#lib/motion.js';

	let { data }: { data: DevExperiments } = $props();

	const KINDS = ['kb', 'injection', 'retrieval', 'answer', 'other'] as const;
	const pct = (v: number | null | undefined) => (v === null || v === undefined ? '-' : `${(v * 100).toFixed(1)}%`);
	const count = (kind: string) => data.runs.filter((r) => r.kind === kind).length;
	const sorted = $derived([...data.runs].sort((a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? '')));
	// The validator only needs a column when some run used an older one; otherwise it is one line under the heading.
	const mixed = $derived(data.kb.some((r) => r.validator_version && r.validator_version !== data.validator_version));
	// A model run twice (two scopes) is told apart by its run name; every other row shows the model alone.
	const repeated = $derived(new Set(data.kb.map((r) => r.model).filter((m, i, all) => all.indexOf(m) !== i)));
	const RECENT = 8;
	let allRuns = $state(false);
	const runs = $derived(allRuns ? sorted : sorted.slice(0, RECENT));
</script>

<!-- Run counts by kind: one compact strip; a kind without runs recedes instead of filling a large tile with 0. -->
<dl class="counts" {@attach revealItems({ step: 35, y: 6 })}>
	{#each KINDS as kind (kind)}
		<div class:zero={!count(kind)}><dt class="label">{t(`dev.run.${kind}` as MessageKey)}</dt><dd {@attach countUp(count(kind))}></dd></div>
	{/each}
</dl>

<section class="panel" aria-labelledby="kb-heading">
	<div class="split">
		<h2 class="heading" id="kb-heading">{t('dev.exp.kb')}</h2>
		<a href="/research/results">{t('dev.exp.openResults')}</a>
	</div>
	{#if data.kb.length && !mixed}<p class="small muted">{t('dev.exp.validator')}: {data.validator_version}</p>{/if}
	{#if data.kb.length}
		<div class="table-scroll">
			<table class="table">
				<thead>
					<tr>
						<th scope="col">{t('dev.col.model')}</th>
						<th scope="col" class="num">{t('dev.report.batches')}</th>
						<th scope="col" class="num">ĐK3</th>
						<th scope="col" class="num">ĐK4</th>
						<th scope="col" class="num">{t('results.col.rejected')}</th>
						<th scope="col" class="num">{t('results.col.injection')}</th>
						{#if mixed}<th scope="col">{t('dev.exp.validator')}</th>{/if}
					</tr>
				</thead>
				<tbody>
					{#each data.kb as r (r.run)}
						<tr>
							<th scope="row"><code title={r.run}>{r.model}</code>{#if repeated.has(r.model)}<span class="small muted run">{r.run}</span>{/if}</th>
							<td class="num">{r.batches_ok}/{r.batches_planned ?? r.batches_attempted}</td>
							<td class="num">{r.dk3_claims}</td>
							<td class="num">{r.dk4_claims}</td>
							<td class="num">{pct(r.rejected_rate)}</td>
							<td class="num">{r.injection ? pct(r.injection.detectable_rate) : '-'}</td>
							{#if mixed}<td>{r.validator_version ?? '-'}{#if r.validator_version && r.validator_version !== data.validator_version}<span class="chip stale">{t('dev.exp.stale')}</span>{/if}</td>{/if}
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{:else}
		<p class="dev-empty">{t('dev.exp.noKb')}</p>
	{/if}
</section>

<div class="dev-two">
	<section class="panel" aria-labelledby="audit-heading">
		<h2 class="heading" id="audit-heading">{t('dev.exp.audits')}</h2>
		{#if data.audits.length}
			{#each data.audits as a (a.name)}
				<div class="audit">
					<p><strong>{a.name}</strong> <span class="small muted">{t('dev.exp.auditItems', { n: a.items })}</span></p>
					{#each a.sheets as s (s.file)}
						<div class="progress-row">
							<span class="small">{s.file}</span>
							<span class="progress" role="progressbar" aria-valuemin="0" aria-valuemax={s.items} aria-valuenow={s.labelled} aria-label={s.file}><span style="width:{s.items ? (s.labelled / s.items) * 100 : 0}%"></span></span>
							<span class="small num">{s.labelled}/{s.items}</span>
						</div>
					{/each}
				</div>
			{/each}
		{:else}
			<p class="dev-empty">{t('dev.exp.noAudits')}</p>
		{/if}
	</section>
	<section class="panel" aria-labelledby="runs-heading">
		<h2 class="heading" id="runs-heading">{t('dev.exp.runs')}</h2>
		<ul class="dev-list">
			{#each runs as r (r.name)}
				<li><span><code>{r.name}</code></span><span class="small muted">{t(`dev.run.${r.kind}` as MessageKey)}{r.created_at ? ` · ${formatDate(r.created_at)}` : ''}</span></li>
			{/each}
		</ul>
		{#if sorted.length > RECENT}
			<div><button type="button" class="btn quiet small" aria-expanded={allRuns} onclick={() => (allRuns = !allRuns)}>{allRuns ? t('dev.exp.fewerRuns') : t('dev.exp.allRuns', { n: sorted.length })}</button></div>
		{/if}
	</section>
</div>

<style>
	.counts {
		display: grid;
		grid-template-columns: repeat(5, minmax(0, 1fr));
		margin: 0;
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: var(--r-panel);
	}
	.counts > div {
		display: grid;
		gap: 2px;
		padding: 10px 16px;
	}
	.counts > div + div {
		border-left: 1px solid var(--rule);
	}
	.counts dd {
		margin: 0;
		font: 600 22px/1.15 var(--serif);
		font-variant-numeric: tabular-nums;
	}
	.counts .zero dd {
		color: var(--muted);
		font-weight: 500;
	}
	/* Narrow screens: one row per kind, the name on the left and the count on the right. */
	@media (max-width: 700px) {
		.counts {
			grid-template-columns: minmax(0, 1fr);
			padding: 4px 14px;
		}
		.counts > div {
			display: flex;
			justify-content: space-between;
			align-items: baseline;
			padding: 7px 0;
		}
		.counts > div + div {
			border-left: 0;
			border-top: 1px solid var(--rule);
		}
		.counts dd {
			font-size: 18px;
		}
	}
	.split {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: 12px;
		flex-wrap: wrap;
	}
	.run {
		display: block;
	}
	.stale {
		margin-left: 6px;
		color: var(--attention);
		border-color: currentColor;
	}
	.audit {
		display: grid;
		gap: 6px;
	}
	.progress-row {
		display: grid;
		grid-template-columns: minmax(80px, max-content) minmax(0, 1fr) 4rem;
		gap: 10px;
		align-items: center;
	}
	.progress {
		height: 8px;
		border-radius: 999px;
		background: var(--desk);
		overflow: hidden;
	}
	.progress span {
		display: block;
		height: 100%;
		background: var(--approve);
	}
</style>
