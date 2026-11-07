<script lang="ts">
	import { page } from '$app/state';
	import Icon from '#lib/components/Icon.svelte';
	import LabelForm from '#lib/components/LabelForm.svelte';
	import ConfirmDialog from '#lib/components/ConfirmDialog.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDate } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { act, notify } from '#lib/toast.svelte.js';
	import type { LabelFields, QuestionDraft, QuestionItem, QuestionWorkspace } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	const id = $derived(page.params.id ?? '');
	let ws = $state<QuestionWorkspace | null>(null);
	let error = $state('');
	let tab = $state<'label' | 'add' | 'draft' | 'exchange'>('label');
	let selected = $state('');
	let fields = $state<LabelFields>({ question_type: null, expected_status: null, relevant_unit_ids: [] });
	let note = $state('');
	let busy = $state(false);
	let mode = $state<'shown' | 'hidden'>('hidden');

	const load = () =>
		api<QuestionWorkspace>(`/api/question-set?id=${encodeURIComponent(id)}`)
			.then((v) => {
				ws = v;
				if (!selected || !v.items.some((i) => i.id === selected)) pick(v.items.find((i) => !i.label) ?? v.items[0]);
			})
			.catch((e) => (error = e.message));

	$effect(() => {
		void id;
		if (canReview(session.account)) load();
	});

	function pick(item?: QuestionItem) {
		selected = item?.id ?? '';
		fields = item?.label ? structuredClone($state.snapshot(item.label.fields)) : { question_type: null, expected_status: null, relevant_unit_ids: [] };
		note = item?.label?.note ?? '';
		tab = 'label';
	}

	const current = $derived(ws?.items.find((i) => i.id === selected));
	const family = $derived(current && ws ? ws.items.filter((i) => i.family_id === current.family_id) : []);
	const frozen = $derived(!!ws?.frozen);
	const canPropose = $derived(!!ws?.proposal_model && ws?.show_proposals === true && !frozen);
	const waiting = $derived(ws?.items.filter((i) => !i.proposal) ?? []);

	const chooseMode = () =>
		act(async () => {
			await api('/api/question-set/mode', { set_id: id, show_proposals: mode === 'shown' });
			await load();
		});

	async function save(next: boolean) {
		if (!current) return;
		busy = true;
		const ok = await act(async () => {
			await api('/api/question-set/label', { set_id: id, question_id: current.id, fields: $state.snapshot(fields), note });
			notify({ key: 'qs.saved', params: { n: current.position } });
		});
		if (ok) {
			const after = ws?.items.find((i) => i.position > current.position && !i.label) ?? ws?.items.find((i) => !i.label && i.id !== current.id);
			await load();
			if (next && after) pick(ws?.items.find((i) => i.id === after.id));
			else pick(ws?.items.find((i) => i.id === current.id));
		}
		busy = false;
	}

	const useProposal = () => {
		if (current?.proposal) fields = structuredClone($state.snapshot(current.proposal.fields));
	};

	// Model calls: one confirmation per batch, then one request per question so progress shows and Stop works.
	let confirmOpen = $state(false);
	let pending = $state<{ kind: 'propose'; ids: string[] } | { kind: 'draft' } | null>(null);
	let progress = $state<{ done: number; total: number } | null>(null);
	let stop = false;

	function askPropose(ids: string[]) {
		pending = { kind: 'propose', ids: ids.slice(0, ws?.proposal_calls_left ?? 0) };
		confirmOpen = true;
	}

	async function runConfirmed() {
		if (!pending) return;
		if (pending.kind === 'draft') return runDraft();
		const ids = pending.ids;
		stop = false;
		progress = { done: 0, total: ids.length };
		for (const qid of ids) {
			if (stop) break;
			const ok = await act(() => api('/api/question-set/propose', { set_id: id, question_id: qid, confirm: true }));
			if (!ok) break;
			progress = { done: progress.done + 1, total: ids.length };
		}
		const done = progress.done;
		progress = null;
		notify({ key: 'qs.proposed', params: { n: done } });
		await load();
		pick(ws?.items.find((i) => i.id === selected));
	}

	// Adding questions by hand.
	let newText = $state('');
	let newFamily = $state('');
	const addQuestion = (event: SubmitEvent) => {
		event.preventDefault();
		return act(async () => {
			const q = await api<QuestionItem>('/api/question-set/question', { set_id: id, text: newText, family_id: newFamily || null });
			notify({ key: 'qs.added', params: { n: q.position } });
			newText = '';
			await load();
		});
	};
	const removeQuestion = (item: QuestionItem) =>
		act(async () => {
			if (!confirm(t('qs.removeConfirm', { n: item.position }))) return;
			await api('/api/question-set/question/remove', { set_id: id, question_id: item.id });
			await load();
		});

	// Drafting with the model from chosen articles.
	let outline = $state<{ unit_id: string; document_title: string; heading: string }[]>([]);
	let outlineFilter = $state('');
	let chosen = $state<string[]>([]);
	let draftCount = $state(4);
	let draft = $state<QuestionDraft | null>(null);
	let draftTexts = $state<string[][]>([]);
	$effect(() => {
		if (tab === 'draft' && !outline.length && ws)
			api<{ articles: typeof outline }>(`/api/question-set/outline?set_id=${encodeURIComponent(id)}`).then((r) => (outline = r.articles));
	});
	const visibleOutline = $derived.by(() => {
		const f = outlineFilter.trim().toLowerCase();
		return (f ? outline.filter((a) => a.heading.toLowerCase().includes(f) || a.unit_id.includes(f)) : outline).slice(0, 200);
	});
	function askDraft() {
		pending = { kind: 'draft' };
		confirmOpen = true;
	}
	async function runDraft() {
		busy = true;
		progress = { done: 0, total: 1 };
		await act(async () => {
			draft = await api<QuestionDraft>('/api/question-set/draft', { set_id: id, unit_ids: chosen, count: draftCount, confirm: true });
			draftTexts = draft.drafts.map((d) => [d.text, ...d.paraphrases]);
			await load();
		});
		progress = null;
		busy = false;
	}
	const acceptDraft = (index: number) =>
		act(async () => {
			if (!draft) return;
			const r = await api<{ added: QuestionItem[] }>('/api/question-set/draft/accept', { set_id: id, draft_id: draft.id, index, texts: draftTexts[index] });
			draft.accepted = [...draft.accepted, index];
			notify({ key: 'qs.draftAccepted', params: { n: r.added.length } });
			await load();
		});

	// Exchange.
	async function importLabels(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		await act(async () => {
			const r = await api<{ annotator_name: string; labels: number }>('/api/question-set/import-labels', { labels: JSON.parse(await file.text()) });
			notify({ key: 'qs.labelsImported', params: { name: r.annotator_name, n: r.labels } });
			await load();
		});
		input.value = '';
	}
	const others = $derived(ws?.annotators.filter((a) => a.annotator !== session.account?.username) ?? []);
	const short = (u: string) => u.split('/').slice(1).join('/') || u;
</script>

<svelte:head><title>{ws?.name ?? t('qs.title')} · Lexora</title></svelte:head>

<div class="page">
	{#if !canReview(session.account)}
		<h1 class="title">{t('common.forbidden.title')}</h1>
	{:else if error}
		<p class="notice error" role="alert">{error}</p>
	{:else if !ws}
		<p class="muted">{t('common.loading')}</p>
	{:else}
		<p class="crumb"><a href="/research/questions"><Icon name="back" size={16} />{t('qs.title')}</a></p>
		<header class="page-head">
			<div>
				<h1 class="title">{ws.name}</h1>
				<p class="facts">
					<span>{t('qs.count', { n: ws.items.length })}</span>
					<span>{t('qs.labelledOf', { done: ws.labelled, n: ws.items.length })}</span>
					<a href="/research/{ws.corpus_id}">{t('qs.onVersion', { n: ws.corpus_version })}</a>
					{#if ws.show_proposals !== null}<span class="chip">{ws.show_proposals ? t('qs.mode.shownChip') : t('qs.mode.hiddenChip')}</span>{/if}
				</p>
				{#if ws.guideline}<details class="guideline"><summary>{t('qs.guideline')}</summary><p class="small">{ws.guideline}</p></details>{/if}
			</div>
		</header>
		{#if frozen}<p class="notice info">{t('qs.frozenNote')}</p>{/if}

		{#if ws.show_proposals === null && !frozen}
			<section class="panel mode">
				<h2 class="heading">{t('qs.mode.title')}</h2>
				<p class="small">{t('qs.mode.lead')}</p>
				<div class="choices">
					<label class="choice"><input type="radio" name="mode" value="hidden" bind:group={mode} /><strong>{t('qs.mode.hidden')}</strong><span>{t('qs.mode.hiddenHint')}</span></label>
					<label class="choice"><input type="radio" name="mode" value="shown" bind:group={mode} /><strong>{t('qs.mode.shown')}</strong><span>{t('qs.mode.shownHint')}</span></label>
				</div>
				<div><button type="button" class="btn primary" onclick={chooseMode}>{t('qs.mode.confirm')}</button></div>
			</section>
		{/if}

		<div class="cols">
			<section class="panel list" aria-labelledby="list-heading">
				<div class="row between">
					<h2 class="heading" id="list-heading">{t('qs.questions')}</h2>
					{#if canPropose && waiting.length}
						<button type="button" class="btn small" disabled={!!progress || !ws.proposal_calls_left} onclick={() => askPropose(waiting.map((i) => i.id))}>{t('qs.proposeAll', { n: Math.min(waiting.length, ws.proposal_calls_left) })}</button>
					{/if}
				</div>
				{#if progress}
					<div class="progress" role="status">
						<span>{t('qs.progress', { done: progress.done, n: progress.total })}</span>
						<progress max={progress.total} value={progress.done}></progress>
						{#if progress.total > 1}<button type="button" class="btn quiet small" onclick={() => (stop = true)}>{t('qs.stop')}</button>{/if}
					</div>
				{/if}
				{#if ws.items.length}
					<ol class="questions">
						{#each ws.items as item (item.id)}
							<li>
								<button type="button" class="q" aria-current={item.id === selected ? 'true' : undefined} onclick={() => pick(item)}>
									<span class="num">{item.position}</span>
									<span class="qtext">{item.text}</span>
									<span class="marks">
										{#if item.label}<Icon name="check" size={16} /><span class="visually-hidden">{t('qs.labelled')}</span>{/if}
										{#if item.origin === 'model'}<span class="tag">AI</span>{/if}
									</span>
								</button>
							</li>
						{/each}
					</ol>
				{:else}
					<p class="muted small">{t('qs.noQuestions')}</p>
				{/if}
			</section>

			<section class="panel work">
				<div class="segmented" role="group" aria-label={t('qs.tools')}>
					<button type="button" aria-pressed={tab === 'label'} onclick={() => (tab = 'label')}>{t('qs.tab.label')}</button>
					<button type="button" aria-pressed={tab === 'add'} disabled={frozen} onclick={() => (tab = 'add')}>{t('qs.tab.add')}</button>
					<button type="button" aria-pressed={tab === 'draft'} disabled={frozen || !ws.proposal_model} title={ws.proposal_model ? '' : t('qs.model.off')} onclick={() => (tab = 'draft')}>{t('qs.tab.draft')}</button>
					<button type="button" aria-pressed={tab === 'exchange'} onclick={() => (tab = 'exchange')}>{t('qs.tab.exchange')}</button>
				</div>

				{#if tab === 'label'}
					{#if !current}
						<p class="muted">{t('qs.pickOne')}</p>
					{:else}
						<div class="question">
							<p class="small muted">{t('qs.questionN', { n: current.position })} · {current.origin === 'model' ? t('qs.origin.model') : t('qs.origin.human', { who: current.created_by })}{#if family.length > 1} · {t('qs.family', { n: family.length })}{/if}</p>
							<p class="serif qbig">{current.text}</p>
							{#if !frozen}<button type="button" class="btn quiet small remove" onclick={() => removeQuestion(current!)}><Icon name="x" size={16} />{t('qs.remove')}</button>{/if}
						</div>

						{#if ws.show_proposals}
							<div class="proposal">
								{#if current.proposal}
									<p class="label">{t('qs.proposal.title')}</p>
									<p class="small">
										<strong>{current.proposal.fields.question_type ? t(`qs.type.${current.proposal.fields.question_type}` as MessageKey) : '-'}</strong> ·
										<strong>{current.proposal.fields.expected_status ? t(`qs.status.${current.proposal.fields.expected_status}` as MessageKey) : '-'}</strong> ·
										{current.proposal.fields.relevant_unit_ids.map(short).join(', ') || t('qs.proposal.noUnits')}
									</p>
									{#if current.proposal.rationale}<p class="small muted">{current.proposal.rationale}</p>{/if}
									{#if !frozen}<button type="button" class="btn small" onclick={useProposal}>{t('qs.proposal.use')}</button>{/if}
								{:else if canPropose}
									<p class="small muted">{t('qs.proposal.none')}</p>
									<button type="button" class="btn small" disabled={!!progress || !ws.proposal_calls_left} onclick={() => askPropose([current!.id])}>{t('qs.proposal.ask')}</button>
								{:else}
									<p class="small muted">{ws.proposal_model ? t('qs.proposal.none') : t('qs.model.off')}</p>
								{/if}
							</div>
						{/if}

						{#if ws.show_proposals === null}
							<p class="notice warn small">{t('qs.mode.first')}</p>
						{:else if frozen}
							{#if current.label}<p class="small">{t('qs.savedAt', { date: formatDate(current.label.updated_at) })}</p>{/if}
						{:else}
							<LabelForm setId={id} bind:fields bind:note seed={current.text} />
							<div class="row actions">
								<button type="button" class="btn" disabled={busy} onclick={() => save(false)}>{t('qs.save')}</button>
								<button type="button" class="btn primary" disabled={busy} onclick={() => save(true)}>{t('qs.saveNext')}<Icon name="arrow" /></button>
								{#if current.label}<span class="small muted">{t('qs.savedAt', { date: formatDate(current.label.updated_at) })}</span>{/if}
							</div>
						{/if}
					{/if}
				{:else if tab === 'add'}
					<form class="fields" onsubmit={addQuestion}>
						<p class="small muted">{t('qs.add.lead')}</p>
						<label class="field"><span>{t('qs.add.text')}</span><textarea rows="3" maxlength="1000" required bind:value={newText} placeholder={t('qs.add.ph')}></textarea></label>
						<label class="field"><span>{t('qs.add.family')}</span>
							<select bind:value={newFamily}>
								<option value="">{t('qs.add.newFamily')}</option>
								{#each ws.items as item (item.id)}<option value={item.family_id}>{t('qs.add.sameAs', { n: item.position, text: item.text.slice(0, 60) })}</option>{/each}
							</select>
							<span class="hint">{t('qs.add.familyHint')}</span>
						</label>
						<div><button class="btn primary" type="submit"><Icon name="plus" />{t('qs.add.submit')}</button></div>
					</form>
				{:else if tab === 'draft'}
					<div class="fields wide">
						<p class="small muted">{t('qs.draft.lead')}</p>
						<label class="field"><span>{t('qs.draft.filter')}</span><input type="search" bind:value={outlineFilter} placeholder={t('qs.draft.filterPh')} /></label>
						<ul class="outline">
							{#each visibleOutline as a (a.unit_id)}
								<li><label class="check"><input type="checkbox" value={a.unit_id} bind:group={chosen} /><span><span class="serif">{a.heading}</span><span class="small muted">{a.document_title}</span></span></label></li>
							{/each}
						</ul>
						<div class="row draft-go">
							<label class="field inline"><span>{t('qs.draft.count')}</span><select bind:value={draftCount}>{#each [2, 3, 4, 5, 6, 8] as n (n)}<option value={n}>{n}</option>{/each}</select></label>
							<button type="button" class="btn primary" disabled={!chosen.length || busy || !ws.proposal_calls_left} onclick={askDraft}>{t('qs.draft.go', { n: chosen.length })}</button>
						</div>
						{#if draft}
							<h3 class="label">{t('qs.draft.results', { n: draft.drafts.length })}</h3>
							<ol class="drafts">
								{#each draft.drafts as d, i (i)}
									<li class:accepted={draft.accepted.includes(i)}>
										<p class="small muted">{t(`qs.type.${d.question_type}` as MessageKey)} · {d.relevant_unit_ids.map(short).join(', ')}</p>
										{#each draftTexts[i] as _, j (j)}
											<label class="field"><span class="small">{j === 0 ? t('qs.draft.main') : t('qs.draft.paraphrase', { n: j })}</span><textarea rows="2" bind:value={draftTexts[i][j]} disabled={draft.accepted.includes(i)}></textarea></label>
										{/each}
										{#if d.rationale}<p class="small muted">{d.rationale}</p>{/if}
										{#if draft.accepted.includes(i)}
											<p class="small ok"><Icon name="check" size={16} />{t('qs.draft.done')}</p>
										{:else}
											<button type="button" class="btn small" onclick={() => acceptDraft(i)}><Icon name="plus" size={16} />{t('qs.draft.accept')}</button>
										{/if}
									</li>
								{/each}
							</ol>
						{/if}
					</div>
				{:else}
					<div class="fields wide">
						<h3 class="label">{t('qs.exchange.send')}</h3>
						<p class="small muted">{t('qs.exchange.sendLead')}</p>
						<div class="row gap">
							<a class="btn" href="/api/question-set/pack?id={id}" download><Icon name="download" />{t('qs.exchange.pack')}</a>
							<a class="btn" href="/api/question-set/labels?id={id}" download aria-disabled={!ws.labelled}><Icon name="download" />{t('qs.exchange.labels')}</a>
						</div>
						<h3 class="label">{t('qs.exchange.receive')}</h3>
						<label class="field"><span>{t('qs.exchange.importLabels')}</span><input type="file" accept=".json,application/json" onchange={importLabels} disabled={frozen} /></label>
						<h3 class="label">{t('qs.exchange.annotators')}</h3>
						{#if ws.annotators.length}
							<ul class="annotators">
								{#each ws.annotators as a (a.annotator)}
									<li>
										<span>{a.annotator_name} <span class="small muted">@{a.annotator}{a.imported ? ` · ${t('qs.exchange.importedTag')}` : ''}</span></span>
										<span class="small">{t('qs.labelledOf', { done: a.labels, n: ws.items.length })}</span>
									</li>
								{/each}
							</ul>
						{:else}
							<p class="small muted">{t('qs.exchange.noAnnotators')}</p>
						{/if}
						{#each others as o (o.annotator)}
							<a class="btn primary compare" href="/research/questions/{id}/compare?other={encodeURIComponent(o.annotator)}">{t('qs.exchange.compare', { name: o.annotator_name })}<Icon name="arrow" /></a>
						{/each}
						{#if ws.frozen}<a class="btn" href="/api/question-set/frozen?id={id}" download><Icon name="lock" />{t('qs.exchange.frozen')}</a>{/if}
					</div>
				{/if}
			</section>
		</div>
	{/if}
</div>

<ConfirmDialog bind:open={confirmOpen} title={t('qs.confirm.title')} confirmLabel={t('qs.confirm.go')} onconfirm={runConfirmed}>
	{#if pending?.kind === 'propose'}
		<p>{t('qs.confirm.propose', { n: pending.ids.length, model: ws?.proposal_model ?? '' })}</p>
		<p class="small muted">{t('qs.confirm.proposeData')}</p>
	{:else if pending?.kind === 'draft'}
		<p>{t('qs.confirm.draft', { n: chosen.length, model: ws?.proposal_model ?? '' })}</p>
		<p class="small muted">{t('qs.confirm.draftData')}</p>
	{/if}
	<p class="small muted">{t('qs.confirm.budget', { left: ws?.proposal_calls_left ?? 0 })}</p>
</ConfirmDialog>

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
		align-items: center;
		margin-top: 10px;
		color: var(--ink-2);
	}
	.guideline {
		margin-top: 10px;
		max-width: 70ch;
	}
	.guideline p {
		white-space: pre-line;
	}
	.mode {
		margin-bottom: 20px;
		display: grid;
		gap: 12px;
	}
	.cols {
		display: grid;
		grid-template-columns: minmax(280px, 0.9fr) minmax(0, 1.6fr);
		gap: 20px;
		align-items: start;
	}
	.panel {
		display: grid;
		gap: 12px;
	}
	.list {
		position: sticky;
		top: calc(var(--topbar) + 16px);
		max-height: calc(100vh - var(--topbar) - 32px);
		grid-template-rows: auto auto 1fr;
		overflow: hidden;
	}
	.between {
		justify-content: space-between;
		gap: 8px;
		flex-wrap: wrap;
	}
	.questions {
		list-style: none;
		margin: 0 -8px;
		padding: 0;
		overflow: auto;
	}
	.q {
		width: 100%;
		display: grid;
		grid-template-columns: 2rem minmax(0, 1fr) auto;
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
	.q:hover {
		background: var(--desk);
	}
	.q[aria-current='true'] {
		background: var(--desk);
		box-shadow: inset 3px 0 0 var(--graphite);
	}
	.num {
		color: var(--muted);
		font-variant-numeric: tabular-nums;
	}
	.qtext {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	.marks {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		color: var(--approve);
	}
	.tag {
		font-size: 11px;
		font-weight: 600;
		padding: 0 5px;
		border-radius: 4px;
		background: var(--hl-object);
		color: var(--ink);
	}
	.progress {
		display: grid;
		grid-template-columns: auto 1fr auto;
		gap: 10px;
		align-items: center;
		font-size: 14px;
	}
	.progress progress {
		width: 100%;
	}
	.question {
		position: relative;
		padding-bottom: 4px;
		border-bottom: 1px solid var(--rule);
	}
	.qbig {
		font-size: 1.25rem;
		line-height: 1.5;
		margin: 6px 0 10px;
		padding-right: 90px;
	}
	.remove {
		position: absolute;
		top: 0;
		right: 0;
	}
	.proposal {
		display: grid;
		gap: 6px;
		justify-items: start;
		padding: 12px 14px;
		border: 1px dashed var(--rule-strong);
		border-radius: var(--r-panel);
		background: #f7f8fb;
	}
	.proposal p {
		margin: 0;
	}
	.actions {
		gap: 10px;
		align-items: center;
	}
	.fields {
		display: grid;
		gap: 14px;
		max-width: 680px;
	}
	.fields.wide {
		max-width: none;
	}
	.outline {
		list-style: none;
		margin: 0;
		padding: 4px 0;
		max-height: 340px;
		overflow: auto;
		border: 1px solid var(--rule);
		border-radius: var(--r-control);
	}
	.outline li {
		padding: 6px 10px;
		border-top: 1px solid var(--rule);
	}
	.outline li:first-child {
		border-top: 0;
	}
	.outline .check > span {
		display: grid;
	}
	.draft-go {
		gap: 14px;
		align-items: flex-end;
	}
	.inline {
		grid-auto-flow: column;
		align-items: center;
		gap: 8px;
	}
	.inline select {
		width: auto;
	}
	.drafts {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 12px;
	}
	.drafts li {
		display: grid;
		gap: 8px;
		justify-items: start;
		padding: 12px 14px;
		border: 1px solid var(--rule);
		border-radius: var(--r-panel);
	}
	.drafts li .field {
		width: 100%;
	}
	.drafts li.accepted {
		background: var(--approve-soft);
		border-color: #b9dcc5;
	}
	.ok {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		color: var(--approve);
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
			max-height: 360px;
		}
	}
</style>
