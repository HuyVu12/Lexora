<script lang="ts">
	import PageGuide from '#lib/components/PageGuide.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import Term from '#lib/components/Term.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDate } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import type { KbRunSummary } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	let data = $state<{ runs: KbRunSummary[]; validator_version: string; folder: string } | null>(null);
	let error = $state('');

	$effect(() => {
		if (canReview(session.account))
			api<{ runs: KbRunSummary[]; validator_version: string; folder: string }>('/api/experiments/kb')
				.then((v) => (data = v))
				.catch((e) => (error = e.message));
	});

	const SLOTS = ['actor', 'action', 'object', 'beneficiary', 'recipient', 'conditions', 'exceptions', 'deadlines', 'quantities', 'outcome'];
	const pct = (v: number | null | undefined) => (v === null || v === undefined ? '-' : `${(v * 100).toFixed(1)}%`);
	const num = (v: number) => v.toLocaleString();
	const cost = (v: number | null) => (v ? `${v.toFixed(2)} USD` : '-');
	const stale = $derived(data ? data.runs.filter((r) => r.validator_version && r.validator_version !== data!.validator_version) : []);

	function reason(code: string) {
		const slot = code.replace(/_not_verbatim$/, '');
		if (slot !== code && SLOTS.includes(slot)) return t('results.reason.notVerbatim', { slot: t(`slot.${slot}` as MessageKey) });
		return t(`results.reason.${code}` as MessageKey) ?? code;
	}
	function failure(code: string) {
		return t(`results.error.${code}` as MessageKey) ?? code;
	}
	const sorted = (map: Record<string, number>) => Object.entries(map).sort((a, b) => b[1] - a[1]);
</script>

<svelte:head><title>{t('results.title')} · Lexora</title></svelte:head>

<div class="page">
	{#if !canReview(session.account)}
		<h1 class="title">{t('common.forbidden.title')}</h1>
		<p class="lead">{t('common.forbidden.body')}</p>
	{:else}
		<header class="page-head">
			<div>
				<h1 class="title">{t('results.title')}</h1>
				<p class="lead">{t('results.lead')}</p>
			</div>
		</header>
		<PageGuide name="results" steps={2} />

		{#if error}
			<p class="notice error" role="alert">{error}</p>
		{:else if !data}
			<p class="muted">{t('common.loading')}</p>
		{:else}
			<section class="panel" aria-labelledby="kb-heading">
				<h2 class="heading" id="kb-heading">{t('results.kb.title')}</h2>
				<p class="small muted">{t('results.kb.lead')}</p>
				{#if stale.length}
					<p class="notice warn small">{t('results.stale', { old: stale[0].validator_version ?? '-', now: data.validator_version })}</p>
				{/if}
				{#if !data.runs.length}
					<p class="muted">{t('results.kb.empty', { folder: data.folder })}</p>
				{:else}
					<div class="table-wrap">
						<table>
							<thead>
								<tr>
									<th scope="col">{t('results.col.model')}</th>
									<th scope="col" class="n">{t('results.col.calls')}</th>
									<th scope="col" class="n">{t('results.col.noAnswer')}</th>
									<th scope="col" class="n"><Term key="dk3">{t('results.col.dk3')}</Term></th>
									<th scope="col" class="n"><Term key="dk4">{t('results.col.dk4')}</Term></th>
									<th scope="col" class="n"><Term key="rejected_claims">{t('results.col.rejected')}</Term></th>
									<th scope="col" class="n"><Term key="modality_unverified">{t('results.col.unverified')}</Term></th>
									<th scope="col" class="n"><Term key="planted_errors">{t('results.col.injection')}</Term></th>
									<th scope="col" class="n">{t('results.col.cost')}</th>
								</tr>
							</thead>
							<tbody>
								{#each data.runs as r (r.run)}
									<tr>
										<th scope="row">
											<code>{r.model}</code>
											<span class="small muted">{t('results.settings', { provider: r.provider, effort: r.effort ?? '-', tokens: r.max_tokens ? t('results.maxTokens', { n: num(r.max_tokens) }) : '' })}</span>
										</th>
										<td class="n">{r.batches_ok}/{r.batches_attempted}</td>
										<td class="n">{r.sentences_without_answer ?? '-'}</td>
										<td class="n">{num(r.dk3_claims)}</td>
										<td class="n">{num(r.dk4_claims)}</td>
										<td class="n">{r.rejected} <span class="muted">({pct(r.rejected_rate)})</span></td>
										<td class="n">{pct(r.modality_unverified_rate)}</td>
										<td class="n">{r.injection ? pct(r.injection.detectable_rate) : '-'}</td>
										<td class="n">{cost(r.cost_usd)}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>

					<div class="details">
						{#each data.runs as r (r.run)}
							<details>
								<summary><Icon name="arrow" size={16} />{t('results.details', { model: r.model })}</summary>
								<div class="detail-body">
									<p class="small muted">{r.run} · {formatDate(r.created_at)} · {t('results.tokens', { prompt: num(r.prompt_tokens), completion: num(r.completion_tokens), calls: r.calls_made })}</p>
									<div class="cols">
										<div>
											<h3 class="label">{t('results.reasons')}</h3>
											{#if Object.keys(r.reasons).length}
												<ul class="plain">{#each sorted(r.reasons) as [code, n] (code)}<li><span>{reason(code)}</span><strong>{n}</strong></li>{/each}</ul>
											{:else}
												<p class="small">{t('results.reasons.none')}</p>
											{/if}
											<h3 class="label">{t('results.errors')}</h3>
											{#if Object.keys(r.batch_errors).length}
												<ul class="plain">{#each sorted(r.batch_errors) as [code, n] (code)}<li><span>{failure(code)}</span><strong>{n}</strong></li>{/each}</ul>
											{:else}
												<p class="small">{t('results.errors.none')}</p>
											{/if}
										</div>
										<div>
											<h3 class="label"><Term key="planted_errors">{t('results.injection.title')}</Term></h3>
											{#if r.injection}
												<p class="small">{t('results.injection.summary', { detect: pct(r.injection.detectable_rate), semantic: pct(r.injection.semantic_rate), fr: pct(r.injection.false_reject_rate), n: r.injection.clean_claims })}</p>
												<ul class="plain">
													{#each Object.entries(r.injection.by_type) as [name, v] (name)}
														<li class:semantic={!v.expected_detectable}><span><code>{name}</code></span><strong>{pct(v.detection_rate)}</strong><span class="small muted">{v.injected}</span></li>
													{/each}
												</ul>
											{:else}
												<p class="small muted">{t('results.injection.none')}</p>
											{/if}
										</div>
									</div>
								</div>
							</details>
						{/each}
					</div>
				{/if}
				<p class="small muted">{t('results.refresh')} <code>python -m legal_ai.cli kb-compare</code></p>
			</section>
		{/if}
	{/if}
</div>

<style>
	.panel {
		display: grid;
		gap: 12px;
	}
	.panel > p {
		margin: 0;
	}
	.table-wrap {
		overflow-x: auto;
	}
	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 14px;
	}
	th,
	td {
		padding: 10px 12px;
		border-bottom: 1px solid var(--rule);
		text-align: left;
		vertical-align: top;
	}
	thead th {
		font-weight: 500;
		color: var(--ink-2);
		border-bottom: 1px solid var(--rule-strong);
	}
	tbody th {
		display: grid;
		gap: 2px;
		font-weight: 500;
	}
	tbody th code {
		white-space: nowrap;
	}
	.n {
		text-align: right;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}
	.details {
		display: grid;
		gap: 6px;
	}
	summary {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		cursor: pointer;
		font-weight: 500;
	}
	details[open] summary :global(svg) {
		transform: rotate(90deg);
	}
	.detail-body {
		display: grid;
		gap: 10px;
		padding: 10px 0 14px 22px;
	}
	.detail-body p {
		margin: 0;
	}
	.cols {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 24px;
	}
	.plain {
		list-style: none;
		margin: 4px 0 12px;
		padding: 0;
		display: grid;
		gap: 4px;
		font-size: 14px;
	}
	.plain li {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto 2.5rem;
		gap: 10px;
		align-items: baseline;
		font-variant-numeric: tabular-nums;
	}
	.plain li:not(:has(:nth-child(3))) {
		grid-template-columns: minmax(0, 1fr) auto;
	}
	.semantic code {
		color: var(--muted);
	}
	@media (max-width: 800px) {
		.cols {
			grid-template-columns: 1fr;
		}
	}
</style>
