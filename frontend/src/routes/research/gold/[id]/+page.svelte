<script lang="ts">
	import PageGuide from '#lib/components/PageGuide.svelte';
	import StepTag from '#lib/components/StepTag.svelte';
	import GoldNormEditor from '#lib/components/GoldNormEditor.svelte';
	import { page } from '$app/state';
	import ConfirmDialog from '#lib/components/ConfirmDialog.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDay } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { act, notify } from '#lib/toast.svelte.js';
	import type { GoldItem, GoldNorm, GoldSample, GoldWorkspace } from '#lib/types.js';

	type Scope = 'all' | 'sample';
	const id = $derived(page.params.id ?? '');
	let ws = $state<GoldWorkspace | null>(null);
	let error = $state('');
	let tab = $state<'label' | 'exchange'>('label');
	// Which sentences the list shows; chosen on the first load (the sample for someone who labels only the sample).
	let scope = $state<Scope | null>(null);
	let selected = $state('');
	let norms = $state<GoldNorm[]>([]);
	let selection = $state('');
	let busy = $state(false);
	let confirmSample = $state(false);
	let sentenceEl = $state<HTMLElement | null>(null);

	const inScope = (v: GoldWorkspace, s: Scope | null) => (s === 'sample' && v.sample ? v.items.filter((i) => i.in_sample) : v.items);
	const share = (value: string) => `${Math.round(Number(value) * 100)}%`;

	const load = () =>
		api<GoldWorkspace>(`/api/gold/set?id=${encodeURIComponent(id)}`)
			.then((v) => {
				ws = v;
				if (scope === null || (scope === 'sample' && !v.sample))
					scope = v.sample && !v.items.some((i) => !i.in_sample && i.norms !== null) ? 'sample' : 'all';
				const list = inScope(v, scope);
				if (!selected || !list.some((i) => i.key === selected)) pick(list.find((i) => i.norms === null) ?? list[0]);
			})
			.catch((e) => (error = e.message));

	function setScope(next: Scope) {
		scope = next;
		const list = ws ? inScope(ws, next) : [];
		if (!list.some((i) => i.key === selected)) pick(list.find((i) => i.norms === null) ?? list[0]);
	}

	async function declareSample() {
		await act(async () => {
			const made = await api<GoldSample>('/api/gold/sample', { set_id: id });
			notify({ key: 'gold.sample.declared', params: { n: made.article_count } });
			await load();
		});
	}

	$effect(() => {
		void id;
		if (canReview(session.account)) load();
	});

	// The phrase selected inside the sentence, kept while the annotator moves to a "Fill" button.
	$effect(() => {
		const track = () => {
			const s = document.getSelection();
			if (!s || s.isCollapsed || !sentenceEl) return;
			if (sentenceEl.contains(s.anchorNode) && sentenceEl.contains(s.focusNode)) selection = s.toString().trim();
		};
		document.addEventListener('selectionchange', track);
		return () => document.removeEventListener('selectionchange', track);
	});

	function pick(item?: GoldItem) {
		selected = item?.key ?? '';
		norms = item?.norms ? structuredClone($state.snapshot(item.norms)) : [];
		selection = '';
		tab = 'label';
	}

	const index = $derived(ws ? ws.items.findIndex((i) => i.key === selected) : -1);
	const current = $derived(index >= 0 ? ws?.items[index] : undefined);
	const done = $derived(ws?.items.filter((i) => i.norms !== null).length ?? 0);
	// The listed sentences keep their number in the whole set, so "Câu 12" means the same in both scopes.
	const shown = $derived(ws ? ws.items.map((item, i) => ({ item, n: i + 1 })).filter((x) => scope !== 'sample' || !ws?.sample || x.item.in_sample) : []);
	const shownDone = $derived(shown.filter((x) => x.item.norms !== null).length);
	const sampleOnly = $derived(scope === 'sample' && !!ws?.sample);
	const sampleArticles = $derived.by(() => {
		const found = new Map<string, { id: string; where: string; document: string; n: number }>();
		for (const item of ws?.sample ? ws.items : []) {
			if (!item.in_sample) continue;
			const article = /^(.*?\/article-[^/]+)/.exec(item.unit_id)?.[1] ?? item.unit_id;
			// The path reads "Chương III > Mục 1 > Điều 24 > Khoản 1"; the article is its "Điều" part.
			const parts = item.path.split(' > ');
			const where = parts.find((p) => /^(Điều|Article)\b/.test(p)) ?? parts[parts.length - 1];
			const entry = found.get(article) ?? { id: article, where, document: item.document_title, n: 0 };
			entry.n += 1;
			found.set(article, entry);
		}
		return [...found.values()];
	});
	const others = $derived(ws?.annotators.filter((a) => a.annotator !== ws?.annotator) ?? []);
	const status = (item: GoldItem) =>
		item.norms === null ? t('gold.status.todo') : item.norms.length ? t('gold.status.norms', { n: item.norms.length }) : t('gold.status.none');

	async function save(next: boolean, value: GoldNorm[] = norms) {
		if (!current || !ws) return;
		busy = true;
		const position = index + 1;
		const clean = $state.snapshot(value).map((n) => ({
			modality: n.modality,
			modality_cue: n.modality_cue,
			slots: Object.fromEntries(Object.entries(n.slots).filter(([, v]) => v && v.trim()))
		}));
		const ok = await act(async () => {
			await api('/api/gold/label', { set_id: id, key: current.key, norms: clean });
			notify({ key: clean.length ? 'gold.saved' : 'gold.savedNone', params: { n: position } });
		});
		if (ok) {
			const list = inScope(ws, scope);
			const at = list.findIndex((i) => i.key === current.key);
			const after = list.slice(at + 1).find((i) => i.norms === null) ?? list[at + 1];
			const stay = current.key;
			await load();
			pick(ws?.items.find((i) => i.key === (next && after ? after.key : stay)));
		}
		busy = false;
	}

	async function importLabels(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		await act(async () => {
			const made = await api<{ annotator_name: string; labels: number }>('/api/gold/import-labels', { labels: JSON.parse(await file.text()) });
			notify({ key: 'gold.exchange.imported', params: { n: made.labels, name: made.annotator_name } });
			await load();
		});
		input.value = '';
	}
</script>

<svelte:head><title>{ws?.name ?? t('gold.title')} · Lexora</title></svelte:head>

<div class="page">
	{#if !canReview(session.account)}
		<h1 class="title">{t('common.forbidden.title')}</h1>
	{:else if error}
		<p class="notice error" role="alert">{error}</p>
	{:else if !ws}
		<p class="muted">{t('common.loading')}</p>
	{:else}
		<p class="crumb"><a href="/research/gold"><Icon name="back" size={16} />{t('gold.title')}</a></p>
		<header class="page-head">
			<div>
				<h1 class="title serif">{ws.name}</h1>
				<p class="facts">
					<span>{t('gold.counts', { articles: ws.articles, sentences: ws.sentences })}</span>
					<span>{t('gold.progress', { done, n: ws.items.length })}</span>
					{#if ws.sample}<span>{t('gold.sampleFacts', { articles: ws.sample.article_count, sentences: ws.sample.sentences })}</span>{/if}
					<span>{t('qs.onVersion', { n: ws.corpus_version })}</span>
				</p>
			</div>
		</header>
		<PageGuide name="gold" steps={4} />
		{#if ws.sample}<p class="notice info small sample-note">{t('gold.sample.note', { articles: ws.sample.article_count })}</p>{/if}

		<div class="cols">
			<section class="panel list" aria-labelledby="list-heading">
				<h2 class="heading" id="list-heading">{t('gold.sentences')}</h2>
				{#if ws.sample}
					<div class="segmented scope" role="group" aria-label={t('gold.scope.label')}>
						<button type="button" aria-pressed={!sampleOnly} onclick={() => setScope('all')}>{t('gold.scope.all', { n: ws.items.length })}</button>
						<button type="button" aria-pressed={sampleOnly} onclick={() => setScope('sample')}>{t('gold.scope.sample', { n: ws.sample.sentences })}</button>
					</div>
				{/if}
				<progress class="bar" max={shown.length} value={shownDone}
					aria-label={sampleOnly ? t('gold.progressSample', { done: shownDone, n: shown.length }) : t('gold.progress', { done, n: ws.items.length })}></progress>
				{#if sampleOnly}<p class="small muted scope-progress">{t('gold.progressSample', { done: shownDone, n: shown.length })}</p>{/if}
				<ol class="items">
					{#each shown as { item, n } (item.key)}
						<li>
							<button type="button" class="item" aria-current={item.key === selected ? 'true' : undefined} onclick={() => pick(item)}>
								<span class="num">{n}{#if item.in_sample && !sampleOnly}<span class="dot" aria-hidden="true"></span><span class="visually-hidden">{t('gold.sample.inSample')}</span>{/if}</span>
								<span class="text">{item.text}</span>
								<span class="mark">
									{#if item.norms !== null}<Icon name="check" size={16} />{/if}<span class="visually-hidden">{status(item)}</span>
								</span>
							</button>
						</li>
					{/each}
				</ol>
			</section>

			<section class="panel work">
				<div class="segmented tabs" role="group" aria-label={t('gold.title')}>
					<button type="button" aria-pressed={tab === 'label'} onclick={() => (tab = 'label')}><StepTag n={2} compact />{t('gold.tab.label')}</button>
					<button type="button" aria-pressed={tab === 'exchange'} onclick={() => (tab = 'exchange')}><StepTag n={4} compact />{t('gold.tab.exchange')}</button>
				</div>

				{#if tab === 'label'}
					{#if !current}
						<p class="muted">{t('gold.pickOne')}</p>
					{:else}
						<div class="sentence-box">
							<p class="small muted">
								{t('gold.sentenceN', { n: index + 1 })} · {current.path} · {status(current)}{#if current.in_sample}{' · '}<span class="in-sample">{t('gold.sample.inSample')}</span>{/if}
							</p>
							<p class="small muted doc" title={current.document_title}>{current.document_title}</p>
							{#if current.context}<p class="context small"><span class="label">{t('gold.context')}</span> {current.context}</p>{/if}
							<p class="serif sentence" bind:this={sentenceEl}>{current.text}</p>
							<p class="selection small" aria-live="polite">
								{#if selection}<span class="label">{t('gold.selection')}</span> <mark>{selection}</mark>{:else}<span class="muted">{t('gold.selectionNone')}</span>{/if}
							</p>
						</div>
						<p class="small muted">{t('gold.verbatim')}</p>
						<GoldNormEditor bind:norms slots={ws.slots} modalities={ws.modalities} {selection} disabled={busy} />
						<div class="row actions">
							<button type="button" class="btn" disabled={busy} onclick={() => save(true, [])}>{t('gold.noNorm')}</button>
							<span class="spacer"></span>
							<button type="button" class="btn" disabled={busy || !norms.length} onclick={() => save(false)}>{t('gold.save')}</button>
							<button type="button" class="btn primary" disabled={busy || !norms.length} onclick={() => save(true)}>{t('gold.saveNext')}<Icon name="arrow" /></button>
						</div>
					{/if}
				{:else}
					<div class="fields">
						<h3 class="label">{t('gold.sample.heading')}</h3>
						{#if ws.sample}
							<p class="small">
								{t('gold.sample.info', { articles: ws.sample.article_count, sentences: ws.sample.sentences, share: share(ws.sample.share), seed: ws.sample.seed, who: ws.sample.declared_by, date: formatDay(ws.sample.declared_at) })}
							</p>
							<details class="sample-list">
								<summary>{t('gold.sample.articles', { n: ws.sample.article_count })}</summary>
								<ul>
									{#each sampleArticles as a (a.id)}<li><span><strong>{a.where}</strong> <span class="muted">· {a.document}</span></span><span class="small muted">{t('gold.sentencesN', { n: a.n })}</span></li>{/each}
								</ul>
							</details>
						{:else if ws.sample_declarable}
							<p class="small muted">{t('gold.sample.lead', { articles: ws.sample_defaults.articles, share: share(ws.sample_defaults.share) })}</p>
							<div><button type="button" class="btn" onclick={() => (confirmSample = true)}>{t('gold.sample.declare')}</button></div>
						{:else}
							<p class="small muted">{t('gold.sample.blocked')}</p>
						{/if}
						<h3 class="label">{t('gold.exchange.send')}</h3>
						<p class="small muted">{t('gold.exchange.sendLead')}</p>
						<div class="row gap">
							<a class="btn" href="/api/gold/pack?id={id}" download><Icon name="download" />{t('gold.exchange.pack')}</a>
							<a class="btn" href="/api/gold/labels?id={id}" download aria-disabled={!done}><Icon name="download" />{t('gold.exchange.labels')}</a>
						</div>
						<h3 class="label">{t('gold.exchange.receive')}</h3>
						<label class="field"><span>{t('gold.exchange.importLabels')}</span><input type="file" accept=".json,application/json" onchange={importLabels} /></label>
						<h3 class="label">{t('gold.exchange.annotators')}</h3>
						{#if ws.annotators.length}
							<ul class="annotators">
								{#each ws.annotators as a (a.annotator)}
									<li>
										<span>{a.annotator_name} <span class="small muted">@{a.annotator}{a.imported ? ` · ${t('gold.exchange.importedTag')}` : ''}</span></span>
										<span class="small">{t('gold.labelledBy', { who: a.annotator, n: a.labels })}</span>
									</li>
								{/each}
							</ul>
						{:else}
							<p class="small muted">{t('gold.exchange.noAnnotators')}</p>
						{/if}
						{#each others as o (o.annotator)}
							<a class="btn primary compare" href="/research/gold/{id}/compare?other={encodeURIComponent(o.annotator)}">{t('gold.exchange.compare', { name: o.annotator_name })}<Icon name="arrow" /></a>
						{/each}
						{#if !ws.blockers.length}<a class="btn compare" href="/api/gold/file?id={id}" download><Icon name="download" />{t('gold.exchange.file')}</a>{/if}
					</div>
				{/if}
			</section>
		</div>
		<ConfirmDialog bind:open={confirmSample} title={t('gold.sample.confirmTitle')} confirmLabel={t('gold.sample.confirmGo')} onconfirm={declareSample}>
			<p>{t('gold.sample.confirmBody', { articles: ws.sample_defaults.articles, total: ws.articles, share: share(ws.sample_defaults.share), seed: ws.sample_defaults.seed })}</p>
		</ConfirmDialog>
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
	.facts {
		display: flex;
		flex-wrap: wrap;
		gap: 6px 18px;
		margin-top: 10px;
		color: var(--ink-2);
	}
	.cols {
		display: grid;
		grid-template-columns: minmax(260px, 0.8fr) minmax(0, 1.7fr);
		gap: 20px;
		align-items: start;
	}
	.panel {
		display: grid;
		gap: 12px;
	}
	.sample-note {
		margin: 0 0 16px;
	}
	.list {
		position: sticky;
		top: calc(var(--topbar) + 16px);
		max-height: calc(100vh - var(--topbar) - 32px);
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}
	.scope {
		align-self: flex-start;
		max-width: 100%;
	}
	.scope button {
		padding: 5px 11px;
		white-space: nowrap;
	}
	.bar {
		width: 100%;
		flex: none;
	}
	.scope-progress {
		margin: -6px 0 0;
	}
	.items {
		list-style: none;
		margin: 0 -8px;
		padding: 0;
		overflow: auto;
		flex: 1;
		min-height: 0;
	}
	.item {
		width: 100%;
		display: grid;
		grid-template-columns: 2.6rem minmax(0, 1fr) 18px;
		gap: 8px;
		align-items: start;
		text-align: left;
		padding: 8px;
		border: 0;
		border-radius: var(--r-control);
		background: none;
		font: inherit;
		color: inherit;
		cursor: pointer;
	}
	.item:hover {
		background: var(--desk);
	}
	.item[aria-current='true'] {
		background: var(--desk);
		box-shadow: inset 3px 0 0 var(--graphite);
	}
	.num {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		height: 1.5em;
		color: var(--muted);
		font-variant-numeric: tabular-nums;
	}
	.dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: var(--approve);
		flex: none;
	}
	.in-sample {
		color: var(--approve);
		font-weight: 500;
	}
	.sample-list summary {
		cursor: pointer;
		color: var(--ink-2);
	}
	.sample-list ul {
		list-style: none;
		margin: 8px 0 0;
		padding: 0;
	}
	.sample-list li {
		display: flex;
		justify-content: space-between;
		gap: 12px;
		padding: 6px 0;
		border-top: 1px solid var(--rule);
	}
	.sample-list li .small {
		white-space: nowrap;
	}
	.text {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	.mark {
		color: var(--approve);
	}
	.tabs {
		justify-self: start;
	}
	.tabs button {
		display: inline-flex;
		align-items: center;
		white-space: nowrap;
	}
	.sentence-box {
		display: grid;
		gap: 8px;
		padding-bottom: 12px;
		border-bottom: 1px solid var(--rule);
	}
	.sentence-box p {
		margin: 0;
	}
	.doc {
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}
	.context {
		color: var(--ink-2);
		max-width: 75ch;
	}
	.sentence {
		font-size: 1.3rem;
		line-height: 1.6;
		max-width: 70ch;
	}
	.sentence::selection {
		background: var(--hl-action, #ffe36e);
	}
	.selection mark {
		background: var(--hl-object, #ffe36e);
		padding: 0 3px;
		border-radius: 3px;
	}
	.actions {
		gap: 10px;
		align-items: center;
		flex-wrap: wrap;
	}
	.spacer {
		flex: 1;
	}
	.fields {
		display: grid;
		gap: 14px;
		max-width: 680px;
	}
	.gap {
		gap: 10px;
		flex-wrap: wrap;
	}
	.annotators {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.annotators li {
		display: flex;
		justify-content: space-between;
		gap: 12px;
		padding: 8px 0;
		border-top: 1px solid var(--rule);
	}
	.compare {
		justify-self: start;
	}
	@media (max-width: 1000px) {
		.cols {
			grid-template-columns: 1fr;
		}
		.list {
			position: static;
			max-height: 440px;
		}
	}
</style>
