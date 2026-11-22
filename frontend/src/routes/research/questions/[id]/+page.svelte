<script lang="ts">
	import PageGuide from '#lib/components/PageGuide.svelte';
	import StepTag from '#lib/components/StepTag.svelte';
	import ItemRail from '#lib/components/ItemRail.svelte';
	import Tabs from '#lib/components/Tabs.svelte';
	import WorkspaceSkeleton from '#lib/components/WorkspaceSkeleton.svelte';
	import { rise, DUR } from '#lib/motion.js';
	import '#lib/components/workspace.css';
	import { page } from '$app/state';
	import Skeleton from '#lib/components/Skeleton.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import Term from '#lib/components/Term.svelte';
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
	const railItems = $derived(
		(ws?.items ?? []).map((i) => ({
			key: i.id,
			n: i.position,
			text: i.text,
			done: !!i.label,
			status: i.label ? t('qs.labelled') : t('gold.status.todo'),
			ai: i.origin === 'model'
		}))
	);

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
	{:else}
		<p class="crumb"><a href="/research/questions"><Icon name="back" size={16} />{t('qs.title')}</a></p>
		<header class="page-head">
			<div>
				<h1 class="title serif">{#if ws}{ws.name}{:else}<span class="title-ghost" style:width="min(420px, 70vw)"><Skeleton height="30px" /></span>{/if}</h1>
				<p class="facts">
					{#if ws}
						<span>{t('qs.count', { n: ws.items.length })}</span>
						<span>{t('qs.labelledOf', { done: ws.labelled, n: ws.items.length })}</span>
						<a href="/research/{ws.corpus_id}">{t('qs.onVersion', { n: ws.corpus_version })}</a>
						{#if ws.show_proposals !== null}<span class="chip"><Term key="proposal_mode">{ws.show_proposals ? t('qs.mode.shownChip') : t('qs.mode.hiddenChip')}</Term></span>{/if}
					{:else}<span><Skeleton width="120px" height="12px" /></span><span><Skeleton width="150px" height="12px" /></span><span><Skeleton width="110px" height="12px" /></span>{/if}
				</p>
				{#if ws?.guideline}<details class="guideline"><summary>{t('qs.guideline')}</summary><p class="small">{ws.guideline}</p></details>{/if}
			</div>
		</header>
		<PageGuide name="qset" steps={5} />
		{#if !ws}
			<WorkspaceSkeleton tabs={4} />
		{:else}
		{#if frozen}<p class="notice info">{t('qs.frozenNote')}</p>{/if}

		{#if ws.show_proposals === null && !frozen}
			<section class="panel mode">
				<h2 class="heading"><StepTag n={1} />{t('qs.mode.title')}</h2>
				<p class="small">{t('qs.mode.lead')}</p>
				<div class="choices">
					<label class="choice"><input type="radio" name="mode" value="hidden" bind:group={mode} /><strong>{t('qs.mode.hidden')}</strong><span>{t('qs.mode.hiddenHint')}</span></label>
					<label class="choice"><input type="radio" name="mode" value="shown" bind:group={mode} /><strong>{t('qs.mode.shown')}</strong><span>{t('qs.mode.shownHint')}</span></label>
				</div>
				<div><button type="button" class="btn primary" onclick={chooseMode}>{t('qs.mode.confirm')}</button></div>
			</section>
		{/if}

		<div class="ws-cols">
			<ItemRail
				heading={t('qs.questions')}
				items={railItems}
				{selected}
				onpick={(key) => pick(ws?.items.find((i) => i.id === key))}
				done={ws.labelled}
				total={ws.items.length}
				progress={t('qs.labelledOf', { done: ws.labelled, n: ws.items.length })}
				empty={t('qs.noQuestions')}>
				{#snippet head()}
					{#if canPropose && waiting.length && ws}
						<button type="button" class="btn small propose" disabled={!!progress || !ws.proposal_calls_left} onclick={() => askPropose(waiting.map((i) => i.id))}>{t('qs.proposeAll', { n: Math.min(waiting.length, ws.proposal_calls_left) })}</button>
					{/if}
					{#if progress}
						<div class="calls" role="status">
							<span>{t('qs.progress', { done: progress.done, n: progress.total })}</span>
							<span class="meter"><i style:transform="scaleX({progress.total ? progress.done / progress.total : 0})"></i></span>
							{#if progress.total > 1}<button type="button" class="btn quiet small" onclick={() => (stop = true)}>{t('qs.stop')}</button>{/if}
						</div>
					{/if}
				{/snippet}
				{#snippet marker(item)}
					<span class="marks">
						{#if item.ai}<span class="tag"><Term key="ai" focusable={false}>AI</Term></span>{/if}
						<span class="tick" class:on={item.done} aria-hidden="true">{#if item.done}<Icon name="check" size={12} />{/if}</span>
					</span>
				{/snippet}
			</ItemRail>

			<section class="panel ws-work" aria-label={t('qs.tools')}>
				<Tabs
					bind:value={tab}
					label={t('qs.tools')}
					idPrefix="qs-tab"
					tabs={[
						{ id: 'add', label: t('qs.tab.add'), step: 2, disabled: frozen },
						{ id: 'draft', label: t('qs.tab.draft'), step: 2, disabled: frozen || !ws.proposal_model, title: ws.proposal_model ? '' : t('qs.model.off') },
						{ id: 'label', label: t('qs.tab.label'), step: 3 },
						{ id: 'exchange', label: t('qs.tab.exchange'), step: 4 }
					]} />

				{#if tab === 'label'}
					{#if !current}
						<p class="muted">{t('qs.pickOne')}</p>
					{:else}
						{#key current.id}
							<div class="ws-item" in:rise={{ y: 0, duration: DUR.press }}>
								<div class="ws-where">
									<p>
										<strong>{t('qs.questionN', { n: current.position })}</strong>
										<span>{current.origin === 'model' ? t('qs.origin.model') : t('qs.origin.human', { who: current.created_by })}</span>
										{#if family.length > 1}<span><Term key="paraphrase_family">{t('qs.family', { n: family.length })}</Term></span>{/if}
									</p>
									<span class="ws-state" class:done={!!current.label}>{current.label ? t('qs.labelled') : t('gold.status.todo')}</span>
								</div>
								<p class="serif ws-text">{current.text}</p>
								{#if !frozen}<div><button type="button" class="btn quiet small remove" onclick={() => removeQuestion(current!)}><Icon name="x" size={16} />{t('qs.remove')}</button></div>{/if}
							</div>
						{/key}

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
							<div class="row ws-actions">
								<button type="button" class="btn" disabled={busy} onclick={() => save(false)}>{t('qs.save')}</button>
								<button type="button" class="btn primary" disabled={busy} onclick={() => save(true)}>{t('qs.saveNext')}<Icon name="arrow" /></button>
								{#if current.label}<span class="small muted">{t('qs.savedAt', { date: formatDate(current.label.updated_at) })}</span>{/if}
							</div>
						{/if}
					{/if}
				{:else if tab === 'add'}
					<form class="fields ws-form" onsubmit={addQuestion}>
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
					<div class="ws-groups">
						<section>
							<h3 class="label">{t('qs.exchange.send')}</h3>
							<p class="small muted">{t('qs.exchange.sendLead')}</p>
							<div class="row">
								<a class="btn" href="/api/question-set/pack?id={id}" download><Icon name="download" />{t('qs.exchange.pack')}</a>
								<a class="btn" href="/api/question-set/labels?id={id}" download aria-disabled={!ws.labelled}><Icon name="download" />{t('qs.exchange.labels')}</a>
							</div>
						</section>
						<section>
							<h3 class="label">{t('qs.exchange.receive')}</h3>
							<label class="field"><span>{t('qs.exchange.importLabels')}</span><input type="file" accept=".json,application/json" onchange={importLabels} disabled={frozen} /></label>
						</section>
						<section>
							<h3 class="label">{t('qs.exchange.annotators')}</h3>
							{#if ws.annotators.length}
								<ul class="ws-people">
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
							{#if others.length || ws.frozen}
								<div class="row">
									{#each others as o (o.annotator)}
										<a class="btn primary" href="/research/questions/{id}/compare?other={encodeURIComponent(o.annotator)}"><StepTag n={5} compact />{t('qs.exchange.compare', { name: o.annotator_name })}<Icon name="arrow" /></a>
									{/each}
									{#if ws.frozen}<a class="btn" href="/api/question-set/frozen?id={id}" download><Icon name="lock" />{t('qs.exchange.frozen')}</a>{/if}
								</div>
							{/if}
						</section>
					</div>
				{/if}
			</section>
		</div>
		{/if}
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
	.facts a {
		color: inherit;
	}
	.guideline {
		margin-top: 10px;
		max-width: 70ch;
	}
	.guideline summary {
		cursor: pointer;
		color: var(--ink-2);
		font-size: 14px;
	}
	.guideline p {
		white-space: pre-line;
		margin-top: 6px;
	}
	.mode {
		margin-bottom: var(--space-5);
		display: grid;
		gap: 12px;
	}
	.propose {
		justify-self: start;
	}
	.calls {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto;
		gap: 10px;
		align-items: center;
		font-size: 13.5px;
	}
	.marks {
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}
	.tag {
		font-size: 11px;
		font-weight: 600;
		padding: 0 5px;
		border-radius: 4px;
		background: var(--hl-object);
		color: var(--ink);
	}
	.tick {
		display: grid;
		place-items: center;
		width: 18px;
		height: 18px;
		border-radius: 50%;
		border: 1.5px solid var(--rule-strong);
		color: var(--paper);
	}
	.tick.on {
		border-color: var(--approve);
		background: var(--approve);
	}
	.tick :global(svg) {
		stroke-width: 3;
	}
	.remove {
		margin-left: -10px;
		color: var(--muted);
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
</style>
