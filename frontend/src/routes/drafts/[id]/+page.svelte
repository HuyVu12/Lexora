<script lang="ts">
	import PageGuide from '#lib/components/PageGuide.svelte';
	import { onDestroy } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import Steps from '#lib/components/Steps.svelte';
	import Statute, { type Focus } from '#lib/components/Statute.svelte';
	import NormCard from '#lib/components/NormCard.svelte';
	import Term from '#lib/components/Term.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import { api } from '#lib/api.js';
	import { t, unitLabel } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { notify } from '#lib/toast.svelte.js';
	import { selectionAnchor, SelectionError } from '#lib/selection.js';
	import { KEY_GROUPS, slotKey } from '#lib/roles.js';
	import type { Claim, Draft, Unit } from '#lib/types.js';

	let draft = $state<Draft | null>(null);
	let loadError = $state('');
	let focus = $state<Focus>(null);
	let filter = $state<'all' | 'undecided' | 'attention'>('all');
	let busy = $state(false);
	let poll: ReturnType<typeof setTimeout> | undefined;

	const id = $derived(page.params.id ?? '');

	async function load() {
		clearTimeout(poll);
		try {
			draft = await api<Draft>(`/api/draft?id=${encodeURIComponent(id)}`);
			loadError = '';
			if (draft.status === 'merged' && draft.kb) return goto(`/kb/${draft.kb.id}?published=1`, { replaceState: true });
			if (['queued', 'running'].includes(draft.extraction.state)) poll = setTimeout(load, 1500);
			if (!focus) {
				const first = draft.claims.find((c) => !c.decision) ?? draft.claims[0];
				if (first) focus = { kind: 'claim', id: first.id };
			}
		} catch (e) {
			loadError = e instanceof Error ? e.message : String(e);
		}
	}
	$effect(() => {
		void id;
		focus = null;
		if (canReview(session.account)) load();
	});
	onDestroy(() => clearTimeout(poll));

	async function review(itemId: string | null, decision: string, payload?: Record<string, unknown>) {
		draft = await api<Draft>('/api/draft/review', { draft_id: id, item_id: itemId, decision, payload });
	}

	const numbers = $derived(new Map((draft?.claims ?? []).map((c, i) => [c.id, i + 1])));
	const units = $derived(new Map<string, Unit>((draft?.articles ?? []).flatMap((a) => a.units.map((u) => [u.unit_version_id, u] as [string, Unit]))));
	const visible = (c: Claim) => filter === 'all' || (filter === 'undecided' && !c.decision) || (filter === 'attention' && c.reasons.length > 0);
	const focusedClaim = $derived(focus?.kind === 'claim' ? draft?.claims.find((c) => c.id === focus!.id) ?? null : null);
	const focusedGap = $derived(focus?.kind === 'gap' ? draft?.gaps.find((g) => g.id === focus!.id) ?? null : null);
	const decided = $derived(draft ? draft.progress.total - draft.progress.undecided : 0);
	const target = $derived(
		draft ? (draft.target.mode === 'new' ? t('review.target.new', { name: draft.target.name ?? '' }) : t('review.target.merge', { name: draft.kb?.name ?? '' })) : ''
	);
	const articleStats = $derived(
		(draft?.articles ?? []).map((a) => {
			const claims = draft!.claims.filter((c) => c.article_id === a.id);
			const gaps = draft!.gaps.filter((g) => g.article_id === a.id);
			return { article: a, claims, gaps, open: claims.filter((c) => !c.decision).length, openGaps: gaps.filter((g) => !g.decision).length };
		})
	);
	const ext = $derived(draft?.extraction);
	const extNotice = $derived.by(() => {
		if (!ext || ext.mode !== 'llm') return null;
		const p = { model: ext.model, checked: ext.checked, n: ext.ai_claims, codes: ext.errors.join(', ') };
		if (ext.state === 'done' && !ext.checked) return { tone: 'info', text: t('review.ext.noNeed') };
		if (ext.state === 'done' && !ext.ai_claims) return { tone: 'info', text: t('review.ext.none', p) };
		if (ext.state === 'done') return { tone: 'info', text: t('review.ext.done', p) };
		if (ext.state === 'partial') return { tone: 'warn', text: t('review.ext.partial', p), retry: true };
		if (ext.state === 'failed') return { tone: 'error', text: t('review.ext.failed', p), retry: true };
		if (ext.state === 'interrupted') return { tone: 'warn', text: t('review.ext.interrupted'), retry: true };
		return null;
	});

	async function guarded(fn: () => Promise<unknown>) {
		busy = true;
		try {
			await fn();
		} catch (e) {
			notify(e instanceof SelectionError ? t(e.key) : e instanceof Error ? e.message : String(e), true);
		} finally {
			busy = false;
		}
	}

	async function addClaim(anchor: { unit_version_id: string; start: number; end: number }) {
		await review(null, 'add_claim', anchor);
		const added = draft!.claims.find((c) => c.origin === 'manual' && c.quote?.unit_version_id === anchor.unit_version_id && c.quote.start === anchor.start && c.quote.end === anchor.end);
		if (added) focus = { kind: 'claim', id: added.id };
		getSelection()?.removeAllRanges();
	}

	async function discard() {
		if (!confirm(t('review.discardConfirm'))) return;
		await guarded(async () => {
			await api('/api/draft/discard', { draft_id: id });
			notify({ key: 'review.discarded' });
			await goto('/');
		});
	}

	// "Add a norm from the selection" appears beside a live selection on the statute, never as chrome on the paper.
	let selectionAt = $state<{ x: number; y: number } | null>(null);
	$effect(() => {
		const update = () => {
			const sel = getSelection();
			const node = sel && sel.rangeCount && !sel.isCollapsed ? sel.getRangeAt(0).commonAncestorContainer : null;
			const host = node ? (node.nodeType === Node.ELEMENT_NODE ? (node as Element) : node.parentElement) : null;
			if (!host?.closest('.paper [data-uv]')) {
				selectionAt = null;
				return;
			}
			const rect = sel!.getRangeAt(0).getBoundingClientRect();
			selectionAt = { x: Math.max(8, Math.min(rect.left, innerWidth - 320)), y: rect.bottom + 8 };
		};
		document.addEventListener('selectionchange', update);
		window.addEventListener('scroll', update, true);
		return () => {
			document.removeEventListener('selectionchange', update);
			window.removeEventListener('scroll', update, true);
		};
	});
	const provenance = $derived(
		draft ? `${draft.title} · ${/^https:\/\//.test(draft.document.source_url ?? '') ? t('review.provenance.library') : t('review.provenance.upload')}` : ''
	);

	function jump(articleId: string) {
		document.getElementById(`article-${articleId.split('/').pop()}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
	}
</script>

<svelte:head><title>{draft?.title ?? t('steps.2')} · Lexora</title></svelte:head>

{#if !canReview(session.account)}
	<div class="page"><h1 class="title">{t('common.forbidden.title')}</h1><p class="lead">{t('common.forbidden.body')}</p></div>
{:else if loadError}
	<div class="page"><p class="notice error" role="alert">{loadError}</p></div>
{:else if !draft}
	<p class="page muted">{t('common.loading')}</p>
{:else if draft.status !== 'draft'}
	<div class="page"><h1 class="title">{draft.title}</h1><p class="lead">{t('review.cancelled')}</p><a class="btn" href="/import">{t('nav.import')}</a></div>
{:else if ['queued', 'running'].includes(draft.extraction.state)}
	{@const x = draft.extraction}
	{@const pct = x.total ? Math.round((100 * x.done) / x.total) : 0}
	<div class="page narrow">
		<Steps current={2} />
		<h1 class="title">{draft.title}</h1>
		<section class="sheet extracting" aria-live="polite">
			<h2 class="subtitle">{t('review.extracting.title')}</h2>
			<p>{t('review.extracting.body', { model: x.model })}</p>
			<div class="track big" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow={pct}><i style:width="{Math.max(4, pct)}%"></i></div>
			<p class="small muted">{x.total ? t('review.extracting.progress', { done: x.done, total: x.total }) : t('review.extracting.preparing')}</p>
			<p class="small muted">{t('review.extracting.leave')}</p>
		</section>
	</div>
{:else}
	<div class="review">
		<header class="head">
			<Steps current={2} />
			<div class="titlebar">
				<div>
					<h1 class="title">{draft.title}</h1>
					<p class="muted">{target}{#if draft.document.synthetic}<span class="chip synthetic">{t('common.synthetic')}</span>{/if}</p>
				</div>
				<div class="progress">
					<p><strong>{t('review.progress', { done: decided, total: draft.progress.total })}</strong></p>
					<div class="track" role="img" aria-label="{t('review.legend.approved', { n: draft.progress.approved })}, {t('review.legend.rejected', { n: draft.progress.rejected })}">
						<i class="a" style:width="{draft.progress.total ? (100 * draft.progress.approved) / draft.progress.total : 0}%"></i><i
							class="r"
							style:width="{draft.progress.total ? (100 * draft.progress.rejected) / draft.progress.total : 0}%"
						></i>
					</div>
					<p class="legend small">
						<span><i class="a"></i>{t('review.legend.approved', { n: draft.progress.approved })}</span>
						<span><i class="r"></i>{t('review.legend.rejected', { n: draft.progress.rejected })}</span>
						<span><i></i>{t('review.legend.undecided', { n: draft.progress.undecided })}</span>
						{#if draft.progress.gaps}<span><i class="g"></i><Term key="gap">{t('review.legend.gaps', { n: draft.progress.gaps_open })}</Term></span>{/if}
					</p>
				</div>
			</div>
			{#if extNotice}
				<div class="notice {extNotice.tone}">
					<p>{extNotice.text}</p>
					{#if extNotice.retry && !decided}
						<button class="btn small" type="button" disabled={busy} onclick={() => guarded(async () => { draft = await api<Draft>('/api/draft/extract', { draft_id: id }); load(); })}>{t('review.ext.retry')}</button>
					{/if}
				</div>
			{/if}
		</header>
		<PageGuide name="review" steps={4} />

		<div class="grid">
			<aside class="index" aria-label={t('review.index')}>
				<div class="filters" role="group" aria-label={t('review.filter.label')}>
					<button type="button" aria-pressed={filter === 'all'} onclick={() => (filter = 'all')}>{t('review.filter.all')}</button>
					<button type="button" aria-pressed={filter === 'undecided'} onclick={() => (filter = 'undecided')}>{t('review.filter.undecided', { n: draft.progress.undecided + draft.progress.gaps_open })}</button>
					<button type="button" aria-pressed={filter === 'attention'} onclick={() => (filter = 'attention')}><Term key="attention" focusable={false}>{t('review.filter.attention')}</Term></button>
				</div>
				<ol class="articles">
					{#each articleStats as s (s.article.id)}
						<li>
							<button type="button" onclick={() => jump(s.article.id)}>
								<span class="name">{unitLabel(s.article.id)}</span>
								<span class="count" class:done={!s.open && !s.openGaps}>{s.claims.length - s.open}/{s.claims.length}</span>
							</button>
							{#if s.open || s.openGaps}
								<div class="batch">
									{#if s.open}<button type="button" class="btn small" disabled={busy} onclick={() => guarded(() => review(null, 'approve_article', { article_id: s.article.id }))}><Icon name="check" size={14} />{t('review.article.batch', { n: s.open })}</button>{/if}
									{#if s.openGaps}<button type="button" class="btn small" disabled={busy} onclick={() => guarded(() => review(null, 'no_norm_article', { article_id: s.article.id }))}><Icon name="x" size={14} />{t('review.article.noNorm', { n: s.openGaps })}</button>{/if}
								</div>
							{/if}
						</li>
					{/each}
				</ol>
				<div class="key">
					<p class="label">{t('review.key')}</p>
					{#each KEY_GROUPS as g (g.cls)}
						<p class="keyrow"><span class="swatch {g.cls}" aria-hidden="true"></span><span
								>{#each g.slots as slot, i (slot)}{#if i}{', '}{/if}<Term key={slot}>{t(slotKey(slot))}</Term>{/each}</span
							></p>
					{/each}
					<p class="keyrow"><span class="cuebox" aria-hidden="true">phải</span><Term key="modality">{t('review.modalityField')}</Term></p>
				</div>
			</aside>

			<div class="paper sheet">
				{#if !draft.progress.total && !draft.progress.gaps}<p class="notice warn">{t('review.empty')}</p>{/if}
				{#each articleStats as s (s.article.id)}
					{@const claims = s.claims.filter(visible)}
					{@const gaps = filter === 'all' ? s.gaps : s.gaps.filter((g) => !g.decision)}
					{#if filter === 'all' || claims.length || gaps.length}
						<Statute article={s.article} {claims} {gaps} {numbers} {focus} onfocus={(f) => (focus = f)} provenance={s === articleStats[0] ? provenance : ''} />
						{#if !s.claims.length && !s.gaps.length}<p class="small muted">{t('review.article.none')}</p>{/if}
					{/if}
				{/each}
				{#if draft.unassigned_text.trim()}
					<details class="unassigned"><summary>{t('review.unassigned')}</summary><p>{draft.unassigned_text}</p></details>
				{/if}
			</div>

			<aside class="side">
				{#if focusedClaim}
					<NormCard claim={focusedClaim} number={numbers.get(focusedClaim.id) ?? 0} {units} {review} />
				{:else if focusedGap}
					{@const g = focusedGap}
					<article class="sheet gapcard">
						<h2 class="heading"><Term key="gap">{g.decision ? t('review.gap.dismissed') : t('review.gap.title')}</Term></h2>
						<blockquote class="serif">{g.text}</blockquote>
						{#if g.ai_note}<p class="pencil">{g.ai_note}</p>{/if}
						{#if !g.decision}<p class="small muted">{t('review.gap.help')}</p>{/if}
						<div class="row">
							{#if !g.decision}
								<button type="button" class="btn primary" disabled={busy} onclick={() => guarded(() => addClaim({ unit_version_id: g.unit_version_id, start: g.start, end: g.end }))}><Icon name="plus" />{t('review.gap.add')}</button>
							{/if}
							<button type="button" class="btn" aria-pressed={g.decision === 'no_norm'} disabled={busy} onclick={() => guarded(() => review(g.id, g.decision ? 'clear' : 'no_norm'))}>{t('review.gap.notNorm')}</button>
						</div>
					</article>
				{:else}
					<p class="sheet hint">{t('review.choose')}</p>
				{/if}

				{#if draft.target.mode === 'merge' && draft.entities.some((e) => e.suggestions.length)}
					<section class="sheet entities">
						<h2 class="heading"><Term key="entity">{t('entities.title')}</Term></h2>
						<p class="small muted">{t('entities.lead')}</p>
						{#each draft.entities.filter((e) => e.suggestions.length) as e (e.id)}
							{@const owner = draft.claims.find((c) => c.id === e.claim_id)}
							{@const suggestion = e.suggestions.find((s) => s.id === e.target) ?? e.suggestions[0]}
							{@const ready = owner?.decision === 'approve'}
							<div class="entity">
								<p><strong>{e.label}</strong> <span class="small muted">{t('entities.inNew', { n: numbers.get(e.claim_id) ?? 0 })}</span></p>
								<p><strong>{suggestion.label}</strong> <span class="small muted">{t('entities.inKb')}</span></p>
								<div class="row">
									<button type="button" class="btn approve small" disabled={!ready || busy} aria-pressed={e.decision === 'link'} onclick={() => guarded(() => review(e.id, e.decision === 'link' ? 'clear' : 'link', { target: suggestion.id }))}>{t('entities.same')}</button>
									<button type="button" class="btn small" disabled={!ready || busy} aria-pressed={e.decision === 'no_link'} onclick={() => guarded(() => review(e.id, e.decision === 'no_link' ? 'clear' : 'no_link'))}>{t('entities.different')}</button>
									{#if !ready}<span class="small muted">{t('entities.approveFirst')}</span>{/if}
								</div>
							</div>
						{/each}
					</section>
				{/if}
			</aside>
		</div>

		{#if selectionAt}
			<button
				type="button"
				class="btn primary small selection-add"
				style:left="{selectionAt.x}px"
				style:top="{selectionAt.y}px"
				disabled={busy}
				onmousedown={(e) => e.preventDefault()}
				onclick={() => guarded(() => addClaim(selectionAnchor(units)))}><Icon name="plus" />{t('review.addFromSelection')}</button
			>
		{/if}
		<footer class="bar">
			<p>
				{[draft.progress.undecided ? t('review.remaining.norms', { n: draft.progress.undecided }) : '', draft.progress.gaps_open ? t('review.remaining.gaps', { n: draft.progress.gaps_open }) : '']
					.filter(Boolean)
					.join(' · ') || t('review.allDone')}
			</p>
			<div class="row">
				<button type="button" class="btn quiet" disabled={busy} onclick={discard}>{t('review.discard')}</button>
				<a class="btn primary" href="/drafts/{id}/preview">{t('review.preview')}<Icon name="arrow" /></a>
			</div>
		</footer>
	</div>
{/if}

<style>
	.narrow {
		max-width: 760px;
	}
	.extracting {
		margin-top: 24px;
		padding: 28px 32px;
		display: grid;
		gap: 10px;
	}
	.review {
		padding: 24px 24px 0;
	}
	.head {
		max-width: 1560px;
		margin: 0 auto 18px;
		display: grid;
		gap: 14px;
	}
	.titlebar {
		display: flex;
		justify-content: space-between;
		gap: 24px;
		flex-wrap: wrap;
		align-items: flex-end;
	}
	.titlebar .chip {
		margin-left: 10px;
	}
	.progress {
		min-width: 360px;
		display: grid;
		gap: 6px;
	}
	.track {
		height: 8px;
		border-radius: 4px;
		background: #cdd0d0;
		display: flex;
		overflow: hidden;
	}
	.track i {
		display: block;
		height: 100%;
	}
	.track .a,
	.legend .a {
		background: var(--approve);
	}
	.track .r,
	.legend .r {
		background: var(--reject);
	}
	.track.big {
		height: 10px;
		margin-top: 8px;
	}
	.track.big i {
		background: var(--graphite);
		transition: width 0.4s var(--ease-out);
	}
	.legend {
		display: flex;
		gap: 14px;
		flex-wrap: wrap;
		color: var(--ink-2);
	}
	.legend span {
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}
	.legend i {
		width: 9px;
		height: 9px;
		border-radius: 2px;
		background: var(--rule-strong);
	}
	.legend .g {
		background: var(--attention);
	}
	.grid {
		max-width: 1560px;
		margin: 0 auto;
		display: grid;
		grid-template-columns: 250px minmax(0, 1fr) 396px;
		gap: 24px;
		align-items: start;
	}
	.index,
	.side {
		scrollbar-gutter: stable;
		position: sticky;
		top: calc(var(--topbar) + 16px);
		display: grid;
		gap: 16px;
		max-height: calc(100vh - var(--topbar) - 96px);
		overflow-y: auto;
	}
	.filters {
		display: grid;
		gap: 2px;
	}
	.filters button {
		text-align: left;
		padding: 7px 10px;
		border: 0;
		border-radius: var(--r-control);
		background: transparent;
		color: var(--ink-2);
		font-weight: 500;
		cursor: pointer;
	}
	.filters button:hover {
		background: var(--desk-2);
	}
	.filters button[aria-pressed='true'] {
		background: var(--paper);
		color: var(--ink);
		font-weight: 600;
		box-shadow: 0 1px 2px rgb(20 22 24 / 0.1);
	}
	.articles {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 2px;
	}
	.articles > li > button {
		width: 100%;
		display: flex;
		justify-content: space-between;
		gap: 10px;
		padding: 8px 10px;
		border: 0;
		border-radius: var(--r-control);
		background: transparent;
		text-align: left;
		cursor: pointer;
	}
	.articles > li > button:hover {
		background: var(--desk-2);
	}
	.count {
		font-size: 13px;
		color: var(--muted);
	}
	.count.done {
		color: var(--approve);
		font-weight: 600;
	}
	.key {
		display: grid;
		gap: 4px;
		padding-top: 12px;
		border-top: 1px solid var(--rule-strong);
	}
	.keyrow {
		display: flex;
		align-items: baseline;
		gap: 8px;
		font-size: 14px;
	}
	.keyrow .swatch {
		align-self: center;
	}
	.keyrow > span:last-child {
		min-width: 0;
	}
	.index {
		overflow-x: hidden;
	}
	.cuebox {
		font: 13px/1 var(--serif);
		padding: 2px 5px;
		border-radius: 999px;
		box-shadow: 0 0 0 1.5px var(--ink-2);
	}
	.paper {
		--sheet-pad-right: 40px;
		padding: 40px var(--sheet-pad-right) 40px 52px;
		min-height: 60vh;
	}
	.paper :global(.article + .article) {
		margin-top: 18px;
		padding-top: 22px;
		border-top: 1px solid var(--rule);
	}
	.batch {
		display: grid;
		justify-items: start;
		gap: 4px;
		padding: 2px 0 8px 10px;
	}
	.batch .btn {
		min-height: 26px;
		padding: 2px 8px;
		gap: 6px;
		font-size: 13px;
		white-space: normal;
		text-align: left;
		justify-content: flex-start;
	}
	.selection-add {
		position: fixed;
		z-index: 30;
		box-shadow: var(--shadow-pop);
	}
	.unassigned {
		margin-top: 24px;
		color: var(--muted);
	}
	.unassigned p {
		white-space: pre-wrap;
	}
	.hint,
	.gapcard,
	.entities {
		padding: 20px 22px;
	}
	.gapcard,
	.entities {
		display: grid;
		gap: 12px;
	}
	blockquote {
		margin: 0;
		font-size: 16px;
		line-height: 1.7;
		padding-left: 14px;
		border-left: 1px solid var(--rule-strong);
	}
	.entity {
		display: grid;
		gap: 6px;
		padding-top: 12px;
		border-top: 1px solid var(--rule);
	}
	.bar {
		position: sticky;
		bottom: 0;
		z-index: 20;
		margin: 24px -24px 0;
		padding: 12px 24px;
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 16px;
		flex-wrap: wrap;
		background: var(--paper);
		border-top: 1px solid var(--rule);
		box-shadow: 0 -4px 16px rgb(20 22 24 / 0.06);
	}
	@media (max-width: 1280px) {
		.grid {
			grid-template-columns: minmax(0, 1fr) 360px;
		}
		.index {
			display: none;
		}
	}
	@media (max-width: 900px) {
		.grid {
			grid-template-columns: 1fr;
		}
		.side {
			position: static;
			max-height: none;
		}
		.paper {
			padding: 24px 20px;
		}
		.progress {
			min-width: 0;
		}
	}
</style>
