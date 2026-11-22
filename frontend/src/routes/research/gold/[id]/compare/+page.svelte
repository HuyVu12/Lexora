<script lang="ts">
	import PageGuide from '#lib/components/PageGuide.svelte';
	import GoldNormEditor from '#lib/components/GoldNormEditor.svelte';
	import ConfirmDialog from '#lib/components/ConfirmDialog.svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import Skeleton from '#lib/components/Skeleton.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import PageSkeleton from '#lib/components/PageSkeleton.svelte';
	import Term from '#lib/components/Term.svelte';
	import { api } from '#lib/api.js';
	import { t } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { act, notify } from '#lib/toast.svelte.js';
	import type { GoldComparison, GoldFinal, GoldModality, GoldNorm, GoldRowStatus, GoldWorkspace } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	type Item = GoldComparison['items'][number];
	const id = $derived(page.params.id ?? '');
	const other = $derived(page.url.searchParams.get('other') ?? '');
	// The comparison needs the other annotator; a link without one goes back to the set instead of waiting forever.
	$effect(() => {
		if (id && !other) goto(`/research/gold/${id}`, { replaceState: true });
	});
	let report = $state<GoldComparison | null>(null);
	let meta = $state<Pick<GoldWorkspace, 'name' | 'slots' | 'modalities' | 'annotators'> | null>(null);
	let error = $state('');
	let filter = $state<'adjudicate' | 'open' | 'sample' | 'all'>('adjudicate');
	let editing = $state('');
	let draft = $state<GoldNorm[]>([]);
	let confirmBulk = $state(false);

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
	const matches = (i: Item) =>
		filter === 'all' || (filter === 'open' && !i.final) || (filter === 'sample' && i.in_sample) || (filter === 'adjudicate' && i.status === 'disagree');
	const shown = $derived(report ? report.items.filter(matches) : []);
	const pct = (v: number | null | undefined) => (v === null || v === undefined ? '-' : v.toFixed(2));
	const modalityKey = (m: GoldModality) => (m === 'unknown' ? 'modality.unknown' : `modality.${m}`) as MessageKey;
	// A row of the agreement sample is decided only once both annotators have labelled it.
	const decidable = (i: Item) => !i.in_sample || (i.first !== null && i.second !== null);
	const bulkable = $derived(report ? report.plan.agreed + report.plan.single : 0);
	const planRows = $derived(
		report
			? (['final', 'agreed', 'single', 'disagree', 'missing_second', 'unlabelled'] as GoldRowStatus[]).filter((s) => s === 'final' || (report?.plan[s] ?? 0) > 0)
			: []
	);
	// With a sample, rows still missing a label are sample rows, and unlabelled rows lie outside it.
	const planKey = (s: GoldRowStatus) =>
		(report?.sample && (s === 'missing_second' || s === 'unlabelled') ? `gold.cmp.plan.${s}Sample` : `gold.cmp.plan.${s}`) as MessageKey;
	function finalLabel(f: GoldFinal) {
		if (f.kind === 'agreed') return t('gold.cmp.prov.agreed', { who: f.people.map(nameOf).join(', ') });
		if (f.kind === 'single') return t('gold.cmp.prov.single', { who: nameOf(f.people[0]) });
		return t('gold.cmp.final', { who: nameOf(f.people[0]) });
	}

	const decide = (key: string, norms: GoldNorm[]) =>
		act(async () => {
			await api('/api/gold/adjudicate', { set_id: id, key, norms: $state.snapshot(norms) });
			editing = '';
			await load();
		});

	const finalise = () =>
		act(async () => {
			const done = await api<{ agreed: number; single: number }>('/api/gold/finalise', { set_id: id });
			notify({ key: 'gold.cmp.bulkDone', params: { agreed: done.agreed, single: done.single } });
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
	{:else}
		<p class="crumb"><a href="/research/gold/{id}"><Icon name="back" size={16} />{t('gold.cmp.back')}</a></p>
		<header class="page-head">
			<div>
				<h1 class="title serif">{t('gold.cmp.title')}{#if meta}{` · ${meta.name}`}{/if}</h1>
				<p class="lead">{#if report && meta}{t('cmp.lead', { a: nameOf(report.first), b: nameOf(report.second) })}{:else}<Skeleton width="min(520px, 80vw)" height="14px" />{/if}</p>
			</div>
		</header>
		<PageGuide name="goldCompare" steps={3} />
		{#if !report || !meta}
			<PageSkeleton head={false} blocks={2} cols />
		{:else}
		<div class="summary">
			<section class="panel stats" aria-labelledby="agree-heading">
				<h2 class="heading" id="agree-heading">{t('gold.cmp.agreement')}</h2>
				{#if report.sample && report.sample_progress}
					<p class="small sample-line">
						<span><Term key="agreement_sample">{t('gold.sample.heading')}</Term>: {t('gold.cmp.sample', { articles: report.sample.article_count, sentences: report.sample.sentences })}</span>
						{#each [report.first, report.second] as who (who)}
							<span class="muted">{t('gold.cmp.sampleDone', { name: nameOf(who), done: report.sample_progress[who] ?? 0, n: report.sample.sentences })}</span>
						{/each}
					</p>
				{:else}
					<p class="small muted">{t('gold.cmp.noSample')}</p>
				{/if}
				<p class="small muted">{t('gold.cmp.both', { done: report.labelled_by_both, n: report.sentences })}</p>
				{#if report.agreement}
					<dl class="numbers">
						<div><dt><Term key="kappa">{t('gold.cmp.kappaHas')}</Term></dt><dd>{pct(report.agreement.kappa_has_norm)}</dd></div>
						<div><dt><Term key="kappa">{t('gold.cmp.kappaMod', { n: report.agreement.matched_norm_pairs })}</Term></dt><dd>{pct(report.agreement.kappa_modality_matched)}</dd></div>
						<div><dt><Term key="f1_strict">{t('gold.cmp.f1Strict')}</Term></dt><dd>{pct(report.agreement.f1_strict.norms)}</dd></div>
						<div><dt><Term key="f1_lenient">{t('gold.cmp.f1Lenient')}</Term></dt><dd>{pct(report.agreement.f1_lenient.norms)}</dd></div>
						<div><dt><Term key="f1_strict">{t('gold.cmp.slotF1')}</Term></dt><dd>{pct(report.agreement.f1_strict.slots)}</dd></div>
					</dl>
				{/if}
			</section>

			<section class="panel finals" aria-labelledby="final-heading">
				<h2 class="heading" id="final-heading"><Term key="adjudication">{t('gold.cmp.finalHeading')}</Term></h2>
				<dl class="plan">
					{#each planRows as s (s)}
						<div class:attention={s === 'disagree' || s === 'missing_second'}><dt>{t(planKey(s))}</dt><dd>{report.plan[s]}</dd></div>
					{/each}
				</dl>
				<p class="small muted">{t('gold.cmp.bulkLead')}</p>
				<div><button type="button" class="btn" disabled={!bulkable} onclick={() => (confirmBulk = true)}><Icon name="check" />{t('gold.cmp.bulk')}</button></div>
				{#if report.blockers.length}
					<div class="notice small blockers" role="status">
						<p>{t('gold.cmp.notReady')}</p>
						<ul>{#each report.blockers as b (b.kind)}<li>{t(`gold.block.${b.kind}` as MessageKey, { n: b.n })}</li>{/each}</ul>
					</div>
				{:else}
					<p class="small">{t('gold.cmp.ready')}</p>
					<a class="btn primary download" href="/api/gold/file?id={id}" download><Icon name="download" />{t('gold.exchange.file')}</a>
				{/if}
			</section>
		</div>

		<div class="segmented filter" role="group" aria-label={t('gold.cmp.title')}>
			<button type="button" aria-pressed={filter === 'adjudicate'} onclick={() => (filter = 'adjudicate')}>{t('gold.cmp.filter.toAdjudicate', { n: report.plan.disagree })}</button>
			<button type="button" aria-pressed={filter === 'open'} onclick={() => (filter = 'open')}>{t('gold.cmp.filter.disagree')}</button>
			{#if report.sample}<button type="button" aria-pressed={filter === 'sample'} onclick={() => (filter = 'sample')}>{t('gold.cmp.filter.sample')}</button>{/if}
			<button type="button" aria-pressed={filter === 'all'} onclick={() => (filter = 'all')}>{t('gold.cmp.filter.all')}</button>
		</div>

		{#if !shown.length}
			<p class="muted">{t('gold.cmp.empty')}</p>
		{/if}
		<ol class="rows">
			{#each shown as item (item.key)}
				<li class="panel row-card" class:decided={!!item.final}>
					<p class="serif sentence">{item.text}</p>
					<p class="small muted meta">
						{#if item.in_sample}<span class="chip public">{t('gold.cmp.inSample')}</span>{/if}
						<span>{item.unit_id}{#if item.agree}{' · '}{t('gold.cmp.agree')}{:else if item.status === 'disagree'}{' · '}{t('gold.cmp.differ')}{/if}</span>
					</p>
					<div class="sides">
						<div>
							<h3 class="label">{nameOf(report.first)}</h3>
							{@render normList(item.first)}
							{#if item.first !== null && !item.final && decidable(item)}<button type="button" class="btn small" onclick={() => decide(item.key, item.first ?? [])}>{t('gold.cmp.useFirst', { name: nameOf(report.first) })}</button>{/if}
						</div>
						<div>
							<h3 class="label">{nameOf(report.second)}</h3>
							{@render normList(item.second)}
							{#if item.second !== null && !item.final && decidable(item)}<button type="button" class="btn small" onclick={() => decide(item.key, item.second ?? [])}>{t('gold.cmp.useSecond', { name: nameOf(report.second) })}</button>{/if}
						</div>
					</div>
					{#if item.final}
						<div class="final">
							<h3 class="label"><Icon name="check" size={16} />{finalLabel(item.final)}</h3>
							{@render normList(item.final.norms)}
						</div>
					{/if}
					{#if !decidable(item)}
						<p class="small muted">{t('gold.cmp.waitSecond')}</p>
					{:else if editing === item.key}
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
		<ConfirmDialog bind:open={confirmBulk} title={t('gold.cmp.bulkTitle')} confirmLabel={t('gold.cmp.bulkGo', { n: bulkable })} onconfirm={finalise}>
			<p>{t('gold.cmp.bulkBody', { agreed: report.plan.agreed, single: report.plan.single })}</p>
		</ConfirmDialog>
		{/if}
	{/if}
</div>

<style>
	.panel {
		display: grid;
		gap: 10px;
		align-content: start;
	}
	.summary {
		display: grid;
		grid-template-columns: minmax(0, 1.5fr) minmax(280px, 1fr);
		gap: 20px;
		align-items: start;
		margin-bottom: 20px;
	}
	.stats p,
	.finals p {
		margin: 0;
	}
	.sample-line {
		display: flex;
		flex-wrap: wrap;
		gap: 4px 16px;
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
	.plan {
		margin: 0;
		display: grid;
	}
	.plan div {
		display: flex;
		justify-content: space-between;
		gap: 12px;
		padding: 6px 0;
		border-top: 1px solid var(--rule);
	}
	.plan div:first-child {
		border-top: 0;
	}
	.plan dt {
		color: var(--ink-2);
	}
	.plan dd {
		margin: 0;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}
	.plan .attention dd {
		color: var(--attention);
	}
	.blockers ul {
		margin: 6px 0 0;
		padding-left: 1.2rem;
	}
	.download {
		justify-self: start;
	}
	/* One row that scrolls sideways on a phone instead of wrapping into a ragged block. */
	.filter {
		margin-bottom: 14px;
		max-width: 100%;
		overflow-x: auto;
		scrollbar-width: none;
	}
	.filter button {
		white-space: nowrap;
		flex: none;
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
	.meta {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 4px 8px;
		overflow-wrap: anywhere;
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
	@media (max-width: 1000px) {
		.summary {
			grid-template-columns: 1fr;
		}
	}
	@media (max-width: 800px) {
		.sides {
			grid-template-columns: 1fr;
		}
	}
</style>
