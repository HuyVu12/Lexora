<script lang="ts">
	import { page } from '$app/state';
	import Icon from '#lib/components/Icon.svelte';
	import LabelForm from '#lib/components/LabelForm.svelte';
	import { api } from '#lib/api.js';
	import { t } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { act, notify } from '#lib/toast.svelte.js';
	import type { ComparedItem, Comparison, LabelFields, QuestionSetSummary } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	const id = $derived(page.params.id ?? '');
	const other = $derived(page.url.searchParams.get('other') ?? '');
	let report = $state<Comparison | null>(null);
	let summary = $state<QuestionSetSummary | null>(null);
	let error = $state('');
	let filter = $state<'all' | 'disagree' | 'open'>('disagree');
	let editing = $state('');
	let fields = $state<LabelFields>({ question_type: null, expected_status: null, relevant_unit_ids: [] });
	let note = $state('');
	let heldOut = $state(30);

	const load = async () => {
		try {
			[report, summary] = await Promise.all([
				api<Comparison>(`/api/question-set/compare?id=${encodeURIComponent(id)}&other=${encodeURIComponent(other)}`),
				api<QuestionSetSummary>(`/api/question-set?id=${encodeURIComponent(id)}`)
			]);
		} catch (e) {
			error = (e as Error).message;
		}
	};
	$effect(() => {
		void id;
		void other;
		if (canReview(session.account)) load();
	});

	const shown = $derived(
		report?.items.filter((i) => (filter === 'all' ? true : filter === 'disagree' ? !i.agree : !i.final)) ?? []
	);
	const frozen = $derived(!!summary?.frozen);

	function edit(item: ComparedItem) {
		editing = item.id;
		const start = item.final ?? (item.agree ? item.first : null);
		fields = start ? { question_type: start.question_type, expected_status: start.expected_status, relevant_unit_ids: [...start.relevant_unit_ids] }
			: { question_type: null, expected_status: null, relevant_unit_ids: [] };
		note = item.final?.note ?? '';
	}

	const decide = (item: ComparedItem) =>
		act(async () => {
			await api('/api/question-set/adjudicate', { set_id: id, question_id: item.id, fields: $state.snapshot(fields), note });
			notify({ key: 'cmp.decided', params: { n: item.position } });
			editing = '';
			await load();
		});

	const acceptAgreed = () =>
		act(async () => {
			const agreed = report?.items.filter((i) => i.agree && !i.final && i.first) ?? [];
			for (const item of agreed)
				await api('/api/question-set/adjudicate', { set_id: id, question_id: item.id, fields: { question_type: item.first!.question_type, expected_status: item.first!.expected_status, relevant_unit_ids: item.first!.relevant_unit_ids }, note: '' });
			notify({ key: 'cmp.acceptedAgreed', params: { n: agreed.length } });
			await load();
		});

	const freeze = () =>
		act(async () => {
			if (!confirm(t('cmp.freezeConfirm'))) return;
			await api('/api/question-set/freeze', { set_id: id, other, held_out: heldOut / 100 });
			notify({ key: 'cmp.frozen' });
			await load();
		});

	const fmt = (v: number | null) => (v === null ? '-' : v.toFixed(2));
	const pct = (v: number | null) => (v === null ? '-' : `${Math.round(v * 100)}%`);
	const short = (u: string) => u.split('/').slice(1).join('/') || u;
	const sameUnits = (a?: LabelFields | null, b?: LabelFields | null) => !!a && !!b && [...a.relevant_unit_ids].sort().join() === [...b.relevant_unit_ids].sort().join();
	const agreedOpen = $derived(report?.items.filter((i) => i.agree && !i.final).length ?? 0);
</script>

<svelte:head><title>{t('cmp.title')} · Lexora</title></svelte:head>

{#snippet side(label: (LabelFields & { note: string }) | null, versus: (LabelFields & { note: string }) | null)}
	{#if label}
		<p class:diff={versus && label.question_type !== versus.question_type}>{label.question_type ? t(`qs.type.${label.question_type}` as MessageKey) : '-'}</p>
		<p class:diff={versus && label.expected_status !== versus.expected_status}>{label.expected_status ? t(`qs.status.${label.expected_status}` as MessageKey) : '-'}</p>
		<p class="units" class:diff={versus && !sameUnits(label, versus)}>
			{#each label.relevant_unit_ids as u (u)}<code>{short(u)}</code>{:else}<span class="muted">{t('qs.proposal.noUnits')}</span>{/each}
		</p>
		{#if label.note}<p class="small muted">{label.note}</p>{/if}
	{:else}
		<p class="muted small">{t('cmp.notLabelled')}</p>
	{/if}
{/snippet}

<div class="page">
	{#if !canReview(session.account)}
		<h1 class="title">{t('common.forbidden.title')}</h1>
	{:else if error}
		<p class="notice error" role="alert">{error}</p>
	{:else if !report || !summary}
		<p class="muted">{t('common.loading')}</p>
	{:else}
		<p class="crumb"><a href="/research/questions/{id}"><Icon name="back" size={16} />{summary.name}</a></p>
		<header class="page-head">
			<div>
				<h1 class="title">{t('cmp.title')}</h1>
				<p class="lead">{t('cmp.lead', { a: report.first.name ?? report.first.annotator, b: report.second.name ?? report.second.annotator })}</p>
			</div>
		</header>

		<section class="metrics" aria-label={t('cmp.metrics')}>
			<div><span class="value">{report.labelled_by_both}/{report.questions}</span><span class="small muted">{t('cmp.both')}</span></div>
			<div><span class="value">{fmt(report.kappa_question_type)}</span><span class="small muted">{t('cmp.kappaType')}</span></div>
			<div><span class="value">{fmt(report.kappa_expected_status)}</span><span class="small muted">{t('cmp.kappaStatus')}</span></div>
			<div><span class="value">{fmt(report.mean_unit_dice)}</span><span class="small muted">{t('cmp.dice')}</span></div>
			<div><span class="value">{pct(report.full_agreement)}</span><span class="small muted">{t('cmp.full')}</span></div>
			<div><span class="value">{report.adjudicated}/{report.questions}</span><span class="small muted">{t('cmp.adjudicated')}</span></div>
		</section>
		<p class="small muted modes">
			{t('cmp.modes', {
				a: report.first.name ?? report.first.annotator,
				am: report.first.proposals_shown ? t('qs.mode.shownChip') : t('qs.mode.hiddenChip'),
				b: report.second.name ?? report.second.annotator,
				bm: report.second.proposals_shown ? t('qs.mode.shownChip') : t('qs.mode.hiddenChip')
			})}
			{#if report.first.proposals_shown && report.second.proposals_shown}<strong>{t('cmp.bothShown')}</strong>{/if}
		</p>

		{#if frozen}
			<p class="notice info">{t('cmp.frozenNote', { dev: summary.frozen?.counts.dev ?? 0, held: summary.frozen?.counts.held_out ?? 0 })} <a href="/api/question-set/frozen?id={id}" download>{t('qs.exchange.frozen')}</a></p>
		{/if}

		<div class="row between toolbar">
			<div class="segmented" role="group" aria-label={t('cmp.filter')}>
				<button type="button" aria-pressed={filter === 'disagree'} onclick={() => (filter = 'disagree')}>{t('cmp.filter.disagree')}</button>
				<button type="button" aria-pressed={filter === 'open'} onclick={() => (filter = 'open')}>{t('cmp.filter.open')}</button>
				<button type="button" aria-pressed={filter === 'all'} onclick={() => (filter = 'all')}>{t('cmp.filter.all')}</button>
			</div>
			{#if !frozen && agreedOpen}<button type="button" class="btn" onclick={acceptAgreed}><Icon name="check" />{t('cmp.acceptAgreed', { n: agreedOpen })}</button>{/if}
		</div>

		<ol class="items">
			{#each shown as item (item.id)}
				<li class:agree={item.agree} class:done={!!item.final}>
					<div class="qhead">
						<span class="num">{item.position}</span>
						<p class="serif">{item.text}</p>
						<span class="state small">{item.final ? t('cmp.state.final') : item.agree ? t('cmp.state.agree') : t('cmp.state.disagree')}</span>
					</div>
					<div class="sides">
						<div><p class="label">{report.first.name ?? report.first.annotator}</p>{@render side(item.first, item.second)}</div>
						<div><p class="label">{report.second.name ?? report.second.annotator}</p>{@render side(item.second, item.first)}</div>
						<div class="final"><p class="label">{t('cmp.final')}</p>{#if item.final}{@render side(item.final, null)}<p class="small muted">{t('cmp.decidedBy', { who: item.final.decided_by })}</p>{:else}<p class="small muted">{t('cmp.notDecided')}</p>{/if}</div>
					</div>
					{#if !frozen}
						{#if editing === item.id}
							<div class="editor">
								<LabelForm setId={id} bind:fields bind:note seed={item.text} name="final-{item.id}" />
								<div class="row gap">
									<button type="button" class="btn quiet" onclick={() => (editing = '')}>{t('common.cancel')}</button>
									<button type="button" class="btn primary" onclick={() => decide(item)}>{t('cmp.decide')}</button>
								</div>
							</div>
						{:else}
							<button type="button" class="btn small" onclick={() => edit(item)}><Icon name="edit" size={16} />{item.final ? t('cmp.change') : t('cmp.decideOpen')}</button>
						{/if}
					{/if}
				</li>
			{:else}
				<li class="empty muted">{t('cmp.none')}</li>
			{/each}
		</ol>

		{#if !frozen}
			<section class="panel freeze">
				<h2 class="heading">{t('cmp.freeze')}</h2>
				<p class="small muted">{t('cmp.freezeLead')}</p>
				<label class="field inline"><span>{t('cmp.heldOut')}</span><input type="number" min="10" max="50" step="5" bind:value={heldOut} />%</label>
				<div><button type="button" class="btn primary" disabled={report.adjudicated < report.questions} onclick={freeze}><Icon name="lock" />{t('cmp.freezeGo')}</button></div>
				{#if report.adjudicated < report.questions}<p class="small muted">{t('cmp.freezeNeed', { n: report.questions - report.adjudicated })}</p>{/if}
			</section>
		{/if}
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
	.metrics {
		display: grid;
		grid-template-columns: repeat(6, minmax(0, 1fr));
		gap: 12px;
		margin-bottom: 10px;
	}
	.metrics > div {
		display: grid;
		gap: 2px;
		padding: 14px 16px;
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: var(--r-panel);
	}
	.value {
		font-size: 1.5rem;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}
	.modes {
		margin: 0 0 18px;
	}
	.toolbar {
		justify-content: space-between;
		gap: 10px;
		flex-wrap: wrap;
		margin-bottom: 12px;
	}
	.items {
		list-style: none;
		margin: 0 0 24px;
		padding: 0;
		display: grid;
		gap: 12px;
	}
	.items > li {
		display: grid;
		gap: 12px;
		justify-items: start;
		padding: 16px 18px;
		background: var(--paper);
		border: 1px solid var(--rule);
		border-left: 4px solid var(--attention);
		border-radius: var(--r-panel);
	}
	.items > li.agree {
		border-left-color: var(--approve);
	}
	.items > li.done {
		border-left-color: var(--graphite);
	}
	.items > li.empty {
		border-left-color: var(--rule);
	}
	.qhead {
		display: grid;
		grid-template-columns: 2rem minmax(0, 1fr) auto;
		gap: 10px;
		width: 100%;
		align-items: start;
	}
	.qhead p {
		margin: 0;
		font-size: 1.08rem;
	}
	.num {
		color: var(--muted);
	}
	.state {
		color: var(--ink-2);
		white-space: nowrap;
	}
	.sides {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 16px;
		width: 100%;
	}
	.sides p {
		margin: 0 0 4px;
	}
	.final {
		padding-left: 16px;
		border-left: 1px solid var(--rule);
	}
	.diff {
		background: var(--hl-condition);
		background: color-mix(in srgb, var(--hl-condition) 60%, var(--paper));
		border-radius: 3px;
		padding: 0 4px;
		justify-self: start;
		display: inline-block;
	}
	.units {
		display: flex;
		flex-wrap: wrap;
		gap: 4px 8px;
	}
	.units code {
		font-size: 12.5px;
	}
	.editor {
		width: 100%;
		display: grid;
		gap: 12px;
		padding-top: 12px;
		border-top: 1px solid var(--rule);
	}
	.gap {
		gap: 10px;
	}
	.freeze {
		display: grid;
		gap: 12px;
		max-width: 680px;
	}
	.inline {
		grid-auto-flow: column;
		justify-content: start;
		align-items: center;
		gap: 8px;
	}
	.inline input {
		width: 90px;
	}
	@media (max-width: 1000px) {
		.metrics {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
		.sides {
			grid-template-columns: 1fr;
		}
		.final {
			padding-left: 0;
			border-left: 0;
		}
	}
</style>
