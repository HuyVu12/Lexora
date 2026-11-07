<script lang="ts">
	import PageGuide from '#lib/components/PageGuide.svelte';
	import GoldNormEditor from '#lib/components/GoldNormEditor.svelte';
	import { page } from '$app/state';
	import Icon from '#lib/components/Icon.svelte';
	import { api } from '#lib/api.js';
	import { t } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { act } from '#lib/toast.svelte.js';
	import type { GoldComparison, GoldModality, GoldNorm, GoldWorkspace } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	const id = $derived(page.params.id ?? '');
	const other = $derived(page.url.searchParams.get('other') ?? '');
	let report = $state<GoldComparison | null>(null);
	let meta = $state<Pick<GoldWorkspace, 'name' | 'slots' | 'modalities' | 'annotators'> | null>(null);
	let error = $state('');
	let filter = $state<'open' | 'all'>('open');
	let editing = $state('');
	let draft = $state<GoldNorm[]>([]);

	const load = () =>
		Promise.all([
			api<GoldComparison>(`/api/gold/compare?id=${encodeURIComponent(id)}&other=${encodeURIComponent(other)}`),
			api<GoldWorkspace>(`/api/gold/set?id=${encodeURIComponent(id)}`)
		])
			.then(([r, w]) => {
				report = r;
				meta = { name: w.name, slots: w.slots, modalities: w.modalities, annotators: w.annotators };
			})
			.catch((e) => (error = e.message));

	$effect(() => {
		void id;
		void other;
		if (canReview(session.account)) load();
	});

	const nameOf = (who: string) => meta?.annotators.find((a) => a.annotator === who)?.annotator_name ?? who;
	const shown = $derived(report ? report.items.filter((i) => filter === 'all' || !i.final) : []);
	const pct = (v: number | null | undefined) => (v === null || v === undefined ? '-' : v.toFixed(2));
	const modalityKey = (m: GoldModality) => (m === 'unknown' ? 'modality.unknown' : `modality.${m}`) as MessageKey;

	const decide = (key: string, norms: GoldNorm[]) =>
		act(async () => {
			await api('/api/gold/adjudicate', { set_id: id, key, norms: $state.snapshot(norms) });
			editing = '';
			await load();
		});

	function edit(key: string, norms: GoldNorm[] | null) {
		editing = key;
		draft = structuredClone($state.snapshot(norms ?? []));
	}
</script>

{#snippet normList(norms: GoldNorm[] | null)}
	{#if norms === null}
		<p class="small muted">{t('gold.cmp.notLabelled')}</p>
	{:else if !norms.length}
		<p class="small">{t('gold.status.none')}</p>
	{:else}
		<ol class="norm-list">
			{#each norms as n, i (i)}
				<li>
					<strong>{t(modalityKey(n.modality))}</strong>{#if n.modality_cue}<span class="muted"> ({n.modality_cue})</span>{/if}
					<dl>
						{#each Object.entries(n.slots) as [slot, value] (slot)}<dt>{t(`slot.${slot}` as MessageKey)}</dt><dd>{value}</dd>{/each}
					</dl>
				</li>
			{/each}
		</ol>
	{/if}
{/snippet}

<svelte:head><title>{t('gold.cmp.title')} · Lexora</title></svelte:head>

<div class="page">
	{#if !canReview(session.account)}
		<h1 class="title">{t('common.forbidden.title')}</h1>
	{:else if error}
		<p class="notice error" role="alert">{error}</p>
	{:else if !report || !meta}
		<p class="muted">{t('common.loading')}</p>
	{:else}
		<p class="crumb"><a href="/research/gold/{id}"><Icon name="back" size={16} />{t('gold.cmp.back')}</a></p>
		<header class="page-head">
			<div>
				<h1 class="title serif">{t('gold.cmp.title')} · {meta.name}</h1>
				<p class="lead">{t('gold.cmp.lead')}</p>
			</div>
		</header>
		<PageGuide name="goldCompare" steps={2} />

		<section class="panel stats" aria-labelledby="agree-heading">
			<h2 class="heading" id="agree-heading">{t('gold.cmp.agreement')}</h2>
			<p class="small muted">{t('gold.cmp.both', { done: report.labelled_by_both, n: report.sentences })} · {t('gold.cmp.adjudicated', { done: report.adjudicated, n: report.sentences })}</p>
			{#if report.agreement}
				<dl class="numbers">
					<div><dt>{t('gold.cmp.kappaHas')}</dt><dd>{pct(report.agreement.kappa_has_norm)}</dd></div>
					<div><dt>{t('gold.cmp.kappaMod', { n: report.agreement.matched_norm_pairs })}</dt><dd>{pct(report.agreement.kappa_modality_matched)}</dd></div>
					<div><dt>{t('gold.cmp.f1Strict')}</dt><dd>{pct(report.agreement.f1_strict.norms)}</dd></div>
					<div><dt>{t('gold.cmp.f1Lenient')}</dt><dd>{pct(report.agreement.f1_lenient.norms)}</dd></div>
					<div><dt>{t('gold.cmp.slotF1')}</dt><dd>{pct(report.agreement.f1_strict.slots)}</dd></div>
				</dl>
			{/if}
			{#if report.adjudicated === report.sentences}<a class="btn primary download" href="/api/gold/file?id={id}" download><Icon name="download" />{t('gold.exchange.file')}</a>{/if}
		</section>

		<div class="segmented filter" role="group" aria-label={t('gold.cmp.title')}>
			<button type="button" aria-pressed={filter === 'open'} onclick={() => (filter = 'open')}>{t('gold.cmp.filter.disagree')}</button>
			<button type="button" aria-pressed={filter === 'all'} onclick={() => (filter = 'all')}>{t('gold.cmp.filter.all')}</button>
		</div>

		{#if !shown.length}
			<p class="muted">{t('gold.cmp.empty')}</p>
		{/if}
		<ol class="rows">
			{#each shown as item (item.key)}
				<li class="panel row-card" class:decided={!!item.final}>
					<p class="serif sentence">{item.text}</p>
					<p class="small muted">{item.unit_id}{#if item.agree} · {t('gold.cmp.agree')}{/if}</p>
					<div class="sides">
						<div>
							<h3 class="label">{nameOf(report.first)}</h3>
							{@render normList(item.first)}
							{#if item.first !== null && !item.final}<button type="button" class="btn small" onclick={() => decide(item.key, item.first ?? [])}>{t('gold.cmp.useFirst', { name: nameOf(report.first) })}</button>{/if}
						</div>
						<div>
							<h3 class="label">{nameOf(report.second)}</h3>
							{@render normList(item.second)}
							{#if item.second !== null && !item.final}<button type="button" class="btn small" onclick={() => decide(item.key, item.second ?? [])}>{t('gold.cmp.useSecond', { name: nameOf(report.second) })}</button>{/if}
						</div>
					</div>
					{#if item.final}
						<div class="final">
							<h3 class="label"><Icon name="check" size={16} />{t('gold.cmp.final', { who: item.final.decided_by })}</h3>
							{@render normList(item.final.norms)}
						</div>
					{/if}
					{#if editing === item.key}
						<p class="small muted">{t('gold.verbatim')}</p>
						<GoldNormEditor bind:norms={draft} slots={meta.slots} modalities={meta.modalities} />
						<div class="row gap">
							<button type="button" class="btn primary" onclick={() => decide(item.key, draft)}>{t('gold.cmp.decide')}</button>
							<button type="button" class="btn quiet" onclick={() => (editing = '')}>{t('common.cancel')}</button>
						</div>
					{:else}
						<div><button type="button" class="btn quiet small" onclick={() => edit(item.key, item.final?.norms ?? item.first ?? item.second)}><Icon name="edit" size={16} />{t('gold.cmp.edit')}</button></div>
					{/if}
				</li>
			{/each}
		</ol>
	{/if}
</div>

<style>
	.crumb {
		margin: 0 0 8px;
	}
	.crumb a {
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}
	.panel {
		display: grid;
		gap: 10px;
	}
	.stats {
		margin-bottom: 20px;
	}
	.stats p {
		margin: 0;
	}
	.numbers {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
		gap: 12px;
		margin: 0;
	}
	.numbers div {
		padding: 10px 12px;
		border: 1px solid var(--rule);
		border-radius: var(--r-control);
	}
	.numbers dt {
		font-size: 13px;
		color: var(--muted);
	}
	.numbers dd {
		margin: 4px 0 0;
		font-size: 1.4rem;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}
	.download {
		justify-self: start;
	}
	.filter {
		margin-bottom: 14px;
	}
	.rows {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 14px;
	}
	.row-card.decided {
		border-color: #b9dcc5;
	}
	.sentence {
		margin: 0;
		font-size: 1.15rem;
		line-height: 1.55;
	}
	.row-card > p.small {
		margin: 0;
	}
	.sides {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 16px;
	}
	.sides > div {
		display: grid;
		gap: 8px;
		align-content: start;
		justify-items: start;
	}
	.final {
		padding: 10px 12px;
		border-radius: var(--r-control);
		background: var(--approve-soft);
	}
	.final .label {
		display: inline-flex;
		align-items: center;
		gap: 4px;
	}
	.norm-list {
		margin: 0;
		padding-left: 1.2rem;
		display: grid;
		gap: 6px;
	}
	.norm-list dl {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		gap: 2px 10px;
		margin: 4px 0 0;
		font-size: 14px;
	}
	.norm-list dt {
		color: var(--muted);
	}
	.norm-list dd {
		margin: 0;
	}
	.gap {
		gap: 10px;
	}
	@media (max-width: 800px) {
		.sides {
			grid-template-columns: 1fr;
		}
	}
</style>
