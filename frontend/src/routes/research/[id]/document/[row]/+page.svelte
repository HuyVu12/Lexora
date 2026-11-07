<script lang="ts">
	import { page } from '$app/state';
	import Icon from '#lib/components/Icon.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDay } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import type { CorpusDocumentDetail, ParsedUnit } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	const corpusId = $derived(page.params.id ?? '');
	const row = $derived(page.params.row ?? '');
	let doc = $state<CorpusDocumentDetail | null>(null);
	let error = $state('');
	let filter = $state<'all' | 'audit'>('all');

	$effect(() => {
		void row;
		if (!canReview(session.account)) return;
		doc = null;
		api<CorpusDocumentDetail>(`/api/corpus/document?id=${encodeURIComponent(row)}`)
			.then((v) => (doc = v))
			.catch((e) => (error = e.message));
	});

	const DEPTH = { chapter: 0, section: 1, article: 1, clause: 2, point: 3 } as const;
	// Chapter, section and article units start with their heading line; only that line is bold.
	const HEADED = new Set(['chapter', 'section', 'article']);
	/** [heading line, the rest with its leading line break] of a unit's text. */
	const lines = (u: ParsedUnit) => {
		const text = u.text.trim();
		const cut = text.indexOf(String.fromCharCode(10));
		return cut < 0 ? [text, ''] : [text.slice(0, cut), text.slice(cut)];
	};
	const flagged = $derived(new Set(doc?.audit.map((a) => a.unit_id).filter(Boolean) ?? []));
	const shown = $derived(doc ? (filter === 'audit' ? doc.units.filter((u) => flagged.has(u.unit_id)) : doc.units) : []);
	const AUDIT_CODES = new Set(['duplicate_heading', 'orphan_heading', 'sequence_gap']);
	const auditLabel = (code: string) => (AUDIT_CODES.has(code) ? t(`corpus.audit.${code}` as MessageKey) : code);
	const anchor = (u: ParsedUnit) => 'u-' + u.unit_id.replace(/[^a-z0-9-]/gi, '_');
</script>

<svelte:head><title>{doc?.title ?? t('research.title')} · Lexora</title></svelte:head>

<div class="page">
	{#if !canReview(session.account)}
		<h1 class="title">{t('common.forbidden.title')}</h1>
	{:else if error}
		<p class="notice error" role="alert">{error}</p>
	{:else if !doc}
		<p class="muted">{t('common.loading')}</p>
	{:else}
		<p class="crumb"><a href="/research/{corpusId}"><Icon name="back" size={16} />{t('corpus.backToCorpus')}</a></p>
		<header class="page-head">
			<div>
				<h1 class="title serif">{doc.title}</h1>
				<p class="facts">
					<code>{doc.document_id}</code>
					<span>{t('corpus.doc.counts', { articles: doc.article_count, leaves: doc.leaf_count })}</span>
					{#if doc.metadata.effect_status?.name}<span>{doc.metadata.effect_status.name}</span>{/if}
					{#if doc.source_kind === 'vbpl'}
						<a href={doc.source_url} target="_blank" rel="noopener noreferrer">vbpl.vn · {t('corpus.doc.accessed', { date: formatDay(doc.accessed_at) })}</a>
					{:else}
						<span>{t('corpus.doc.file', { name: doc.source_ref })}</span>
					{/if}
				</p>
				<p class="small muted">SHA-256 <code>{doc.source_sha256}</code></p>
			</div>
		</header>

		{#if doc.removed_at}<p class="notice warn">{t('corpus.doc.removed')}</p>{/if}

		<div class="cols">
			<section class="panel" aria-labelledby="units-heading">
				<div class="row between">
					<h2 class="heading" id="units-heading">{t('corpus.doc.units', { n: doc.unit_count })}</h2>
					<div class="segmented" role="group" aria-label={t('corpus.doc.filter')}>
						<button type="button" aria-pressed={filter === 'all'} onclick={() => (filter = 'all')}>{t('corpus.doc.filter.all')}</button>
						<button type="button" aria-pressed={filter === 'audit'} disabled={!flagged.size} onclick={() => (filter = 'audit')}>{t('corpus.doc.filter.audit', { n: flagged.size })}</button>
					</div>
				</div>
				<ol class="units">
					{#each shown as u (u.unit_id)}
						<li id={anchor(u)} class="d{DEPTH[u.unit_type]} {u.unit_type}" class:flag={flagged.has(u.unit_id)}>
							<span class="uid small muted"><code>{u.unit_id.slice(doc.document_id.length + 1)}</code></span>
							<span class="text" class:serif={u.unit_type !== 'chapter'}>{#if HEADED.has(u.unit_type)}<strong>{lines(u)[0]}</strong>{lines(u)[1]}{:else}{u.text.trim()}{/if}</span>
						</li>
					{/each}
				</ol>
			</section>

			<aside class="panel" id="audit" aria-labelledby="audit-heading">
				<h2 class="heading" id="audit-heading">{t('corpus.doc.auditTitle')}</h2>
				<p class="small muted">{t('corpus.doc.auditLead')}</p>
				{#if doc.audit.length}
					<ul class="audit">
						{#each doc.audit as a, i (i)}
							<li>
								<Icon name="warn" size={16} />
								<span>
									<strong>{auditLabel(a.code)}</strong>
									{#if a.unit_id}<a class="small" href="#{'u-' + a.unit_id.replace(/[^a-z0-9-]/gi, '_')}" onclick={() => (filter = 'all')}><code>{a.unit_id.slice(doc.document_id.length + 1)}</code></a>{/if}
									<span class="small muted">{t('corpus.doc.offset', { n: a.offset })}</span>
								</span>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="small">{t('corpus.doc.noAudit')}</p>
				{/if}
				{#if doc.unassigned_text.trim()}
					<h3 class="label">{t('corpus.doc.unassigned', { n: doc.unassigned_characters })}</h3>
					<pre class="unassigned">{doc.unassigned_text.trim()}</pre>
				{/if}
			</aside>
		</div>
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
		grid-template-columns: minmax(0, 1.7fr) minmax(0, 1fr);
		gap: 20px;
		align-items: start;
	}
	.panel {
		display: grid;
		gap: 12px;
	}
	.between {
		justify-content: space-between;
		flex-wrap: wrap;
		gap: 10px;
	}
	.units {
		list-style: none;
		margin: 0;
		padding: 0;
		max-height: 75vh;
		overflow: auto;
	}
	.units li {
		display: grid;
		grid-template-columns: 11rem minmax(0, 1fr);
		gap: 12px;
		padding: 6px 4px;
		border-top: 1px solid var(--rule);
		scroll-margin-top: calc(var(--topbar) + 12px);
	}
	.units li:target {
		background: var(--attention-soft);
	}
	.units .text {
		white-space: pre-line;
	}
	.d2 .text {
		padding-left: 16px;
	}
	.d3 .text {
		padding-left: 32px;
	}
	.units strong {
		font-weight: 700;
	}
	.flag {
		box-shadow: inset 3px 0 0 var(--attention);
	}
	.uid {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.audit {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 10px;
	}
	.audit li {
		display: grid;
		grid-template-columns: 16px minmax(0, 1fr);
		gap: 8px;
		color: var(--attention);
	}
	.audit li > span {
		display: grid;
		gap: 2px;
		color: var(--ink);
	}
	.unassigned {
		margin: 0;
		white-space: pre-wrap;
		font-size: 0.85rem;
		background: var(--desk);
		padding: 10px 12px;
		border-radius: var(--r-control);
		max-height: 240px;
		overflow: auto;
	}
	@media (max-width: 1000px) {
		.cols {
			grid-template-columns: 1fr;
		}
	}
</style>
