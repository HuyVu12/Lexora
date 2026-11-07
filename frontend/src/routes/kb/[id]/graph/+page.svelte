<script lang="ts">
	import { page } from '$app/state';
	import GraphCanvas from '#lib/components/GraphCanvas.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import Term from '#lib/components/Term.svelte';
	import { api } from '#lib/api.js';
	import { t, unitLabel } from '#lib/i18n/index.svelte.js';
	import { GraphIndex, allNormsElements, normElements, roleClass, structureElements, type GEdge, type GNode, type Graph } from '#lib/graph.js';
	import { KEY_GROUPS, ROLE_CLASS, SLOT_ORDER, modalityKey, modalityTerm, slotKey } from '#lib/roles.js';
	import type { KbDetail } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	let kb = $state<KbDetail | null>(null);
	let data = $state<{ revision: string; graph: Graph } | null>(null);
	let error = $state('');
	let view = $state<'norms' | 'structure'>('norms');
	let query = $state('');
	let onlyStructured = $state(true);
	let normId = $state<string | null>(null);
	let picked = $state<{ group: 'nodes' | 'edges'; id: string } | null>(null);
	let scope = $state<'one' | 'all'>('one');
	let focusId = $state<string | null>(null);
	// Side columns and the guide remember the reader's choice on this machine.
	const stored = (key: string, fallback: boolean) => {
		const v = localStorage.getItem(key);
		return v === null ? fallback : v === '1';
	};
	let showList = $state(stored('lexora-graph-list', true));
	let showDetail = $state(stored('lexora-graph-detail', true));
	let guideOpen = $state(!stored('lexora-graph-guide-seen', false));
	$effect(() => localStorage.setItem('lexora-graph-list', showList ? '1' : '0'));
	$effect(() => localStorage.setItem('lexora-graph-detail', showDetail ? '1' : '0'));
	function closeGuide() {
		guideOpen = false;
		localStorage.setItem('lexora-graph-guide-seen', '1');
	}
	const id = $derived(page.params.id ?? '');

	$effect(() => {
		void id;
		Promise.all([api<KbDetail>(`/api/kb?id=${encodeURIComponent(id)}`), api<{ revision: string; graph: Graph }>(`/api/kb/graph?id=${encodeURIComponent(id)}`)])
			.then(([k, g]) => {
				kb = k;
				data = g;
			})
			.catch((e) => (error = e.message));
	});

	const index = $derived(data ? new GraphIndex(data.graph) : null);
	const norms = $derived.by(() => {
		if (!index) return [];
		const q = query.trim().toLocaleLowerCase('vi');
		return index.norms.filter(
			(n) => (!onlyStructured || n.payload.semantic_extraction) && (!q || `${index.title(n)} ${index.unitOf(n)} ${unitLabel(index.unitOf(n))}`.toLocaleLowerCase('vi').includes(q))
		);
	});
	$effect(() => {
		// Keep a norm in focus: the current one while it matches, else the first that does.
		if (norms.length && !norms.some((n) => n.id === normId)) normId = norms[0].id;
		if (!norms.length) normId = null;
	});
	$effect(() => {
		if (view === 'norms' && normId) picked = { group: 'nodes', id: normId };
	});

	const SLOT_OF_EDGE: Record<string, string> = {
		HAS_ACTOR: 'actor', HAS_ACTION: 'action', HAS_OBJECT: 'object', HAS_BENEFICIARY: 'beneficiary', HAS_RECIPIENT: 'recipient',
		HAS_COUNTERPARTY: 'counterparty', HAS_CONDITION: 'conditions', HAS_EXCEPTION: 'exceptions', HAS_QUANTITY: 'quantities',
		HAS_DEADLINE: 'deadlines', HAS_OUTCOME: 'outcome'
	};
	function roleName(n: GNode): string {
		if (n.kind === 'Modality') return t(modalityKey(n.label));
		if (n.kind === 'NormClaim') return t('graph.norm');
		if (n.kind === 'LegalUnit') return t('graph.source');
		if (n.kind === 'Document') return t('graph.document');
		return n.payload?.slot_name && (SLOT_ORDER as readonly string[]).includes(n.payload.slot_name) ? t(slotKey(n.payload.slot_name)) : n.kind;
	}
	function relation(e: GEdge): string {
		if (e.kind === 'HAS_MODALITY') return t('review.modalityField');
		if (SLOT_OF_EDGE[e.kind]) return t(slotKey(SLOT_OF_EDGE[e.kind]));
		return { EXTRACTED_FROM: t('graph.rel.from'), REVIEWED_ENTITY_LINK: t('graph.rel.link'), PART_OF: t('graph.rel.part'), REFERENCES: t('graph.rel.ref') }[e.kind] ?? e.kind;
	}
	const unitKind = (n: GNode) => {
		const key = `unit.${n.payload.unit_type}` as MessageKey;
		const text = t(key);
		return text.charAt(0).toUpperCase() + text.slice(1);
	};

	const elements = $derived.by(() => {
		if (!index) return [];
		if (view === 'structure') return structureElements(index, { unit: unitKind, document: t('graph.document'), norm: t('graph.norm') });
		const labels = { norm: t('graph.norm'), source: t('graph.source'), modality: t('review.modalityField'), role: roleName };
		if (scope === 'all') return allNormsElements(index, norms, labels);
		return normId ? normElements(index, normId, labels) : [];
	});
	const articles = $derived(index ? index.graph.nodes.filter((n) => n.kind === 'LegalUnit' && n.payload.unit_type === 'article') : []);

	const pickedNode = $derived(picked?.group === 'nodes' && index ? index.nodes.get(picked.id) ?? null : null);
	const pickedEdge = $derived(picked?.group === 'edges' && index ? index.graph.edges.find((e) => e.id === picked!.id) ?? null : null);
	function evidenceOf(ids: string[] | undefined) {
		return [...new Set(ids ?? [])].map((eid) => index!.evidence.get(eid)).filter(Boolean) as NonNullable<ReturnType<GraphIndex['evidence']['get']>>[];
	}
	const pickedEvidence = $derived.by(() => {
		if (!index) return [];
		if (pickedEdge) return evidenceOf(pickedEdge.evidence_ids);
		if (!pickedNode) return [];
		if (pickedNode.kind === 'NormClaim') {
			const own = evidenceOf(pickedNode.payload.evidence_ids).filter((e) => e.unit_version_id === pickedNode.payload.source_unit_version_ids?.[0]);
			return own.sort((a, b) => b.quote.length - a.quote.length).slice(0, 1);
		}
		if (pickedNode.kind === 'LegalUnit') {
			const ids = index.graph.edges.filter((e) => e.source === pickedNode.id && e.kind === 'PART_OF').flatMap((e) => e.evidence_ids ?? []);
			return evidenceOf(ids).filter((e) => e.unit_version_id === pickedNode.payload.unit_version_id).slice(0, 1);
		}
		return evidenceOf(pickedNode.payload.evidence_ids);
	});
	const markClass = $derived(pickedNode && pickedNode.kind !== 'NormClaim' && pickedNode.kind !== 'LegalUnit' ? roleClass(pickedNode) : '');
	const linkReview = $derived(
		pickedNode && index ? index.graph.edges.find((e) => e.kind === 'REVIEWED_ENTITY_LINK' && (e.source === pickedNode.id || e.target === pickedNode.id)) ?? null : null
	);
	function select(target: { group: 'nodes' | 'edges'; id: string }) {
		picked = target;
		const node = target.group === 'nodes' ? index?.nodes.get(target.id) : null;
		if (node?.kind === 'NormClaim' && view === 'structure') normId = node.id;
	}
	function openNorm(idOfNorm: string) {
		normId = idOfNorm;
		picked = { group: 'nodes', id: idOfNorm };
		if (scope === 'all') focusId = idOfNorm;
	}
	const docUrl = (docId: string) => index?.document(docId)?.payload.source_url ?? '';
</script>

<svelte:head><title>{t('graph.title')} · {kb?.name ?? 'Lexora'}</title></svelte:head>

<div class="graph-page">
	{#if error}
		<p class="page notice error" role="alert">{error}</p>
	{:else if !kb || !index || !data}
		<p class="page muted">{t('common.loading')}</p>
	{:else}
		<header class="head">
			<div>
				<a class="back" href="/kb/{kb.id}"><Icon name="back" size={16} />{t('graph.back')}</a>
				<h1 class="title">{t('graph.title')} · {kb.name}</h1>
				<p class="small muted">
					{t('graph.stats', { norms: index.norms.length, units: index.units.size, revision: data.revision.slice(0, 8) })}
					{#if data.graph.summary?.synthetic}<span class="chip synthetic">{t('common.synthetic')}</span>{/if}
				</p>
			</div>
			<div class="toolbar">
				<div class="segmented" role="group" aria-label={t('graph.tab.label')}>
					<button type="button" aria-pressed={view === 'norms'} onclick={() => (view = 'norms')}>{t('graph.tab.norms')}</button>
					<button type="button" aria-pressed={view === 'structure'} onclick={() => { view = 'structure'; picked = null; }}>{t('graph.tab.structure')}</button>
				</div>
				{#if view === 'norms'}
					<div class="segmented" role="group" aria-label={t('graph.scope.label')}>
						<button type="button" aria-pressed={scope === 'one'} onclick={() => (scope = 'one')}>{t('graph.scope.one')}</button>
						<button type="button" aria-pressed={scope === 'all'} onclick={() => (scope = 'all')}>{t('graph.scope.all')}</button>
					</div>
				{/if}
				<div class="row" role="group" aria-label={t('graph.panel.label')}>
					<button type="button" class="btn small" aria-pressed={showList} onclick={() => (showList = !showList)}>{t('graph.panel.list')}</button>
					<button type="button" class="btn small" aria-pressed={showDetail} onclick={() => (showDetail = !showDetail)}>{t('graph.panel.detail')}</button>
					<button type="button" class="btn small" aria-expanded={guideOpen} aria-controls="graph-guide" onclick={() => (guideOpen ? closeGuide() : (guideOpen = true))}><Icon name="info" size={16} />{t('graph.guide.open')}</button>
				</div>
			</div>
		</header>

		{#if guideOpen}
			<section id="graph-guide" class="guide sheet" aria-labelledby="graph-guide-title">
				<div class="guide-head">
					<h2 id="graph-guide-title" class="subtitle">{t('graph.guide.title')}</h2>
					<button type="button" class="btn primary small" onclick={closeGuide}>{t('graph.guide.close')}</button>
				</div>
				<dl>
					<div><dt class="heading">{t('graph.guide.whatHead')}</dt><dd>{t('graph.guide.what')}</dd></div>
					<div><dt class="heading">{t('graph.guide.modesHead')}</dt><dd>{t('graph.guide.modes')}</dd></div>
					<div><dt class="heading">{t('graph.guide.colorsHead')}</dt><dd>{t('graph.guide.colors')}</dd></div>
					<div><dt class="heading">{t('graph.guide.howHead')}</dt><dd>{t('graph.guide.how')}</dd></div>
					<div><dt class="heading">{t('graph.guide.limitsHead')}</dt><dd>{t('graph.guide.limits')}</dd></div>
				</dl>
			</section>
		{/if}

		<div class="grid" class:no-list={!showList} class:no-detail={!showDetail}>
			{#if showList}
			<aside class="side panel" aria-label={view === 'norms' ? t('graph.normList') : t('graph.unitList')}>
				{#if view === 'norms'}
					<label class="field"><span class="visually-hidden">{t('graph.search')}</span><input type="search" placeholder={t('graph.search')} bind:value={query} /></label>
					<label class="check small"><input type="checkbox" bind:checked={onlyStructured} />{t('graph.onlyStructured')}</label>
					<ol class="list">
						{#each norms as n (n.id)}
							<li>
								<button type="button" aria-current={n.id === normId ? 'true' : undefined} onclick={() => openNorm(n.id)}>
									<span class="where small">{unitLabel(index.unitOf(n))}<span class="chip">{t(modalityKey(n.payload.modality))}</span></span>
									<span class="what">{index.title(n)}</span>
								</button>
							</li>
						{:else}
							<li class="small muted">{t('graph.empty')}</li>
						{/each}
					</ol>
				{:else}
					<ol class="list">
						{#each articles as a (a.id)}
							<li><button type="button" aria-current={picked?.id === a.id ? 'true' : undefined} onclick={() => (picked = { group: 'nodes', id: a.id })}>
								<span class="where small">{unitLabel(a.payload.unit_id)}</span><span class="what serif">{a.label}</span></button></li>
						{/each}
					</ol>
				{/if}
				<div class="legend">
					<p class="label">{t('graph.legend')}</p>
					{#each KEY_GROUPS as g (g.cls)}
						<p class="keyrow"><span class="swatch {g.cls}" aria-hidden="true"></span><span
								>{#each g.slots as slot, i (slot)}{#if i}{', '}{/if}<Term key={slot}>{t(slotKey(slot))}</Term>{/each}</span
							></p>
					{/each}
					<p class="keyrow"><span class="box source" aria-hidden="true"></span><Term key="source_unit">{t('graph.source')}</Term></p>
					<p class="keyrow"><span class="box linked" aria-hidden="true"></span><Term key="entity">{t('graph.linked')}</Term></p>
				</div>
			</aside>
			{/if}

			<section class="sheet stage">
				<GraphCanvas
					{elements}
					selected={picked?.id ?? null}
					layout={view === 'structure' ? 'tree' : scope === 'all' ? 'rows' : 'preset'}
					focus={focusId}
					label={view === 'norms' && normId ? t('graph.canvasNorm', { title: index.title(index.nodes.get(normId)!) }) : t('graph.canvasStructure')}
					onselect={select}
				/>
			</section>

			{#if showDetail}
			<aside class="side inspector sheet" aria-live="polite">
				{#if pickedEdge}
					<p class="chip">{t('graph.relation')}</p>
					<h2 class="subtitle">{relation(pickedEdge)}</h2>
					{#each [[t('graph.from'), pickedEdge.source], [t('graph.to'), pickedEdge.target]] as [label, nodeId] (label)}
						<p class="label">{label}</p>
						<button type="button" class="btn small linkish" onclick={() => (picked = { group: 'nodes', id: nodeId })}>{index.nodes.get(nodeId)?.label}</button>
					{/each}
				{:else if pickedNode}
					{@const n = pickedNode}
					<p class="kicker-row">
						<span class="chip {n.kind !== 'NormClaim' && n.kind !== 'LegalUnit' ? `role ${roleClass(n)}` : ''}">{roleName(n)}</span>
						{#if n.kind === 'NormClaim'}<span class="chip {n.payload.human_review ? 'public' : ''}">{n.payload.human_review ? t('graph.reviewed') : t('graph.unstructured')}</span>{/if}
					</p>
					<h2 class="subtitle">{n.kind === 'NormClaim' ? index.title(n) : n.kind === 'Modality' ? roleName(n) : n.label}</h2>
					{#if n.kind === 'NormClaim'}
						<dl class="slots">
							<dt><Term key="modality">{t('review.modalityField')}</Term></dt>
							<dd><span class="chip dark"><Term key={modalityTerm(n.payload.modality)}>{t(modalityKey(n.payload.modality))}</Term></span></dd>
							{#each SLOT_ORDER.filter((s) => n.payload.slots?.[s]) as slot (slot)}
								{@const value = n.payload.slots[slot]}
								<dt><span class="swatch {ROLE_CLASS[slot]}" aria-hidden="true"></span><Term key={slot}>{t(slotKey(slot))}</Term></dt>
								<dd>
									{#if value.state === 'present'}
										<button type="button" class="linkish" onclick={() => (picked = { group: 'nodes', id: `${n.id}/slot/${slot}` })}>{value.text}</button>
									{:else}<span class="muted unknown">{value.state === 'not_present' ? t('review.notPresent') : t('review.unknown')}</span>{/if}
								</dd>
							{/each}
						</dl>
					{/if}
					{#if linkReview?.reviewer}<p class="pencil">{t('graph.linkedBy', { name: linkReview.reviewer })}</p>{/if}
				{:else}
					<p class="muted">{t('graph.pick')}</p>
				{/if}
				{#if pickedEvidence.length}
					<p class="label ev-head">{t('graph.evidence')}</p>
					{#each pickedEvidence as ev (ev.evidence_id)}
						<figure class="evidence">
							<blockquote class="serif" lang="vi"><mark class={markClass || 'plain'}>{ev.quote}</mark></blockquote>
							<p class="small muted">{unitLabel(ev.unit_id)}</p>
							{#if /^https:\/\//.test(docUrl(ev.document_id))}<a class="small" href={docUrl(ev.document_id)} target="_blank" rel="noopener noreferrer">{t('graph.openSource')}</a>{/if}
							<details class="small"><summary>{t('graph.details')}</summary>
								<p>{t('graph.offsets', { start: ev.start, end: ev.end })}</p>
								<p>{t('graph.hash')}: <code>{ev.normalized_sha256}</code></p>
							</details>
						</figure>
					{/each}
				{/if}
				<p class="small muted validity">{t('graph.validity')}</p>
			</aside>
			{/if}
		</div>
	{/if}
</div>

<style>
	.graph-page {
		padding: 20px 24px 24px;
	}
	.head {
		max-width: 1640px;
		margin: 0 auto 16px;
		display: flex;
		justify-content: space-between;
		align-items: flex-end;
		gap: 16px;
		flex-wrap: wrap;
	}
	.back {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-size: 14px;
		margin-bottom: 6px;
	}
	.toolbar {
		display: flex;
		gap: 10px 14px;
		align-items: center;
		flex-wrap: wrap;
	}
	.toolbar .btn[aria-pressed='false'] {
		color: var(--muted);
	}
	.toolbar .btn[aria-pressed='true'] {
		background: var(--paper);
	}
	.guide {
		max-width: 1640px;
		margin: 0 auto 16px;
		padding: 18px 22px 20px;
	}
	.guide-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 12px;
		margin-bottom: 12px;
	}
	.guide dl {
		display: grid;
		grid-template-columns: repeat(5, minmax(0, 1fr));
		gap: 18px;
		margin: 0;
	}
	.guide dd {
		margin: 4px 0 0;
		font-size: 14px;
		color: var(--ink-2);
	}
	.grid.no-list {
		grid-template-columns: minmax(0, 1fr) 360px;
	}
	.grid.no-detail {
		grid-template-columns: 290px minmax(0, 1fr);
	}
	.grid.no-list.no-detail {
		grid-template-columns: minmax(0, 1fr);
	}
	.head .chip {
		margin-left: 8px;
	}
	.grid {
		max-width: 1640px;
		margin: 0 auto;
		display: grid;
		grid-template-columns: 290px minmax(0, 1fr) 360px;
		gap: 16px;
		height: calc(100vh - var(--topbar) - 132px);
		min-height: 560px;
	}
	.side {
		overflow-y: auto;
		display: grid;
		align-content: start;
		gap: 12px;
	}
	.panel {
		padding: 16px;
	}
	.list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 2px;
	}
	.list button {
		width: 100%;
		display: grid;
		gap: 3px;
		text-align: left;
		padding: 9px 10px;
		border: 0;
		border-radius: var(--r-control);
		background: transparent;
		cursor: pointer;
	}
	.list button:hover {
		background: var(--desk);
	}
	.list button[aria-current='true'] {
		background: var(--desk);
		box-shadow: inset 0 0 0 1px var(--ink-2);
	}
	.where {
		display: flex;
		justify-content: space-between;
		gap: 8px;
		color: var(--muted);
	}
	.what {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
		line-height: 1.4;
	}
	.legend {
		display: grid;
		gap: 4px;
		padding-top: 12px;
		border-top: 1px solid var(--rule);
	}
	.keyrow {
		display: flex;
		gap: 8px;
		align-items: baseline;
		font-size: 13.5px;
	}
	.keyrow .swatch,
	.keyrow .box {
		align-self: center;
	}
	.box {
		width: 22px;
		height: 12px;
		border-radius: 3px;
		flex: none;
	}
	.box.source {
		background: var(--desk);
		border: 1px solid var(--rule-strong);
	}
	.box.linked {
		border: 1.5px dashed var(--approve);
	}
	.stage {
		overflow: hidden;
		min-width: 0;
	}
	.inspector {
		padding: 20px 22px;
	}
	.kicker-row {
		display: flex;
		gap: 6px;
		flex-wrap: wrap;
	}
	.chip.role {
		background: var(--hl);
		border-color: rgb(0 0 0 / 0.12);
		color: var(--ink);
	}
	.slots {
		display: grid;
		grid-template-columns: 120px minmax(0, 1fr);
		gap: 8px 12px;
		margin: 0;
		font-size: 14px;
	}
	.slots dt {
		display: flex;
		gap: 8px;
		align-items: center;
		color: var(--ink-2);
	}
	.slots dd {
		margin: 0;
		overflow-wrap: anywhere;
	}
	.unknown {
		font-style: italic;
	}
	.linkish {
		border: 0;
		background: none;
		padding: 0;
		color: var(--focus);
		text-align: left;
		cursor: pointer;
		text-decoration: underline;
		text-decoration-thickness: 1px;
		text-underline-offset: 3px;
	}
	.btn.linkish {
		padding: 4px 0;
		min-height: 0;
		white-space: normal;
	}
	.ev-head {
		padding-top: 6px;
		border-top: 1px solid var(--rule);
	}
	.evidence {
		margin: 0;
		display: grid;
		gap: 6px;
	}
	blockquote {
		margin: 0;
		font-size: 16px;
		line-height: 1.75;
	}
	blockquote mark {
		background: var(--hl);
		color: inherit;
		padding: 1px 2px;
		border-radius: 2px;
		box-decoration-break: clone;
		-webkit-box-decoration-break: clone;
	}
	blockquote mark.plain {
		background: rgb(42 45 48 / 0.06);
		box-shadow: inset 0 -1.5px 0 var(--ink-2);
	}
	code {
		font-size: 12px;
		overflow-wrap: anywhere;
	}
	details summary {
		cursor: pointer;
		color: var(--ink-2);
	}
	.validity {
		padding-top: 10px;
		border-top: 1px solid var(--rule);
	}
	@media (max-width: 1100px) {
		.guide dl {
			grid-template-columns: 1fr 1fr;
		}
	}
	@media (max-width: 1200px) {
		.grid {
			grid-template-columns: 260px minmax(0, 1fr);
			height: auto;
		}
		.stage {
			height: 620px;
		}
		.inspector {
			grid-column: 1 / -1;
		}
	}
	@media (max-width: 760px) {
		.grid {
			grid-template-columns: 1fr;
		}
		.stage {
			height: 460px;
		}
	}
</style>
