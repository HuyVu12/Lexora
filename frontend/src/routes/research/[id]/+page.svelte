<script lang="ts">
	import { page } from '$app/state';
	import Icon from '#lib/components/Icon.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDate, formatDay } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { act, notify } from '#lib/toast.svelte.js';
	import type { CatalogEntry, CorpusDetail, CorpusDocument, CorpusListing, CorpusVersion } from '#lib/types.js';

	const ACCEPT = '.txt,.html,.htm,.docx,.pdf';
	const MAX_FILE = 20_000_000;
	const id = $derived(page.params.id ?? '');

	let corpus = $state<CorpusDetail | null>(null);
	let listing = $state<CorpusListing | null>(null);
	let error = $state('');
	let mode = $state<'search' | 'link' | 'file'>('search');
	let query = $state('');
	let results = $state<CatalogEntry[]>([]);
	let searching = $state(false);
	let reference = $state('');
	let documentId = $state('');
	let fileTitle = $state('');
	let file = $state<File | null>(null);
	let note = $state('');
	let busy = $state(false);
	let pending = $state<{ reference: string; label: string } | null>(null);
	let dialog = $state<HTMLDialogElement | null>(null);

	const load = () =>
		api<CorpusDetail>(`/api/corpus?id=${encodeURIComponent(id)}`)
			.then((v) => (corpus = v))
			.catch((e) => (error = e.message));

	$effect(() => {
		void id;
		if (!canReview(session.account)) return;
		corpus = null;
		load();
		api<CorpusListing>('/api/corpora').then((v) => {
			listing = v;
			if (!v.catalog) mode = v.vbpl_enabled ? 'link' : 'file';
		});
	});

	// Search the offline catalog as the reviewer types; the newest answer wins.
	let ticket = 0;
	$effect(() => {
		const q = query.trim();
		if (!listing?.catalog || q.length < 2) {
			results = [];
			return;
		}
		const mine = ++ticket;
		const timer = setTimeout(async () => {
			searching = true;
			try {
				const found = await api<{ results: CatalogEntry[] }>(`/api/catalog/search?limit=12&q=${encodeURIComponent(q)}`);
				if (mine === ticket) results = found.results;
			} catch (e) {
				if (mine === ticket) notify((e as Error).message, true);
			} finally {
				if (mine === ticket) searching = false;
			}
		}, 250);
		return () => clearTimeout(timer);
	});

	const articles = $derived(corpus?.documents.reduce((n, d) => n + d.article_count, 0) ?? 0);
	const inCorpus = $derived(new Set(corpus?.documents.filter((d) => d.source_kind === 'vbpl').map((d) => d.source_ref) ?? []));

	function askFetch(ref: string, label: string) {
		pending = { reference: ref, label };
		dialog?.showModal();
	}

	async function confirmFetch() {
		if (!pending) return;
		const ref = pending.reference;
		dialog?.close();
		busy = true;
		const ok = await act(async () => {
			const added = await api<CorpusDocument>('/api/corpus/vbpl', { corpus_id: id, reference: ref, document_id: documentId.trim() || null, confirm: true });
			notify({ key: 'corpus.added', params: { title: added.title } });
			reference = '';
			documentId = '';
			await load();
		});
		busy = false;
		pending = null;
		return ok;
	}

	function toBase64(buffer: ArrayBuffer) {
		const bytes = new Uint8Array(buffer);
		let binary = '';
		for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
		return btoa(binary);
	}

	async function upload(event: SubmitEvent) {
		event.preventDefault();
		// currentTarget is gone once the handler awaits, so keep the form now.
		const form = event.currentTarget as HTMLFormElement;
		if (!file) return;
		if (file.size > MAX_FILE) return notify({ key: 'corpus.file.tooBig' }, true);
		busy = true;
		await act(async () => {
			const content_base64 = toBase64(await file!.arrayBuffer());
			const added = await api<CorpusDocument>('/api/corpus/file', {
				corpus_id: id,
				filename: file!.name,
				content_base64,
				title: fileTitle.trim() || null,
				document_id: documentId.trim() || null
			});
			notify({ key: 'corpus.added', params: { title: added.title } });
			file = null;
			fileTitle = '';
			documentId = '';
			form.reset();
			await load();
		});
		busy = false;
	}

	const remove = (d: CorpusDocument) =>
		act(async () => {
			if (!confirm(t('corpus.removeConfirm', { title: d.title }))) return;
			corpus = await api<CorpusDetail>('/api/corpus/remove', { corpus_id: id, document_row: d.id });
		});

	async function freeze(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		await act(async () => {
			const v = await api<CorpusVersion>('/api/corpus/freeze', { corpus_id: id, note });
			notify({ key: 'corpus.frozen', params: { n: v.number } });
			note = '';
			await load();
		});
		busy = false;
	}

	const statusTone = (name?: string | null) =>
		!name ? '' : /^Còn hiệu lực|^Chưa có hiệu lực/.test(name) ? 'ok' : /một phần/.test(name) ? 'partial' : 'gone';
</script>

<svelte:head><title>{corpus?.name ?? t('research.title')} · Lexora</title></svelte:head>

<div class="page">
	{#if !canReview(session.account)}
		<h1 class="title">{t('common.forbidden.title')}</h1>
		<p class="lead">{t('common.forbidden.body')}</p>
	{:else if error}
		<p class="notice error" role="alert">{error}</p>
	{:else if !corpus}
		<p class="muted">{t('common.loading')}</p>
	{:else}
		<p class="crumb"><a href="/research"><Icon name="back" size={16} />{t('research.title')}</a></p>
		<header class="page-head">
			<div>
				<h1 class="title">{corpus.name}</h1>
				{#if corpus.description}<p class="lead">{corpus.description}</p>{/if}
				<p class="facts">
					<span>{t('research.docs', { n: corpus.documents.length })}</span>
					<span>{t('corpus.articles', { n: articles })}</span>
					<span>{corpus.versions.length ? t('research.latest', { n: corpus.versions[0].number }) : t('research.notFrozen')}</span>
				</p>
			</div>
		</header>

		<div class="cols">
			<div class="stack">
				<section class="panel" aria-labelledby="add-heading">
					<h2 class="heading" id="add-heading">{t('corpus.add')}</h2>
					<div class="segmented" role="group" aria-label={t('corpus.add')}>
						<button type="button" aria-pressed={mode === 'search'} onclick={() => (mode = 'search')}><Icon name="search" size={16} />{t('corpus.add.search')}</button>
						<button type="button" aria-pressed={mode === 'link'} onclick={() => (mode = 'link')}><Icon name="link" size={16} />{t('corpus.add.link')}</button>
						<button type="button" aria-pressed={mode === 'file'} onclick={() => (mode = 'file')}><Icon name="upload" size={16} />{t('corpus.add.file')}</button>
					</div>

					{#if mode !== 'file' && listing && !listing.vbpl_enabled}
						<p class="notice warn small">{t('research.vbpl.off')}</p>
					{/if}

					{#if mode === 'search'}
						{#if listing?.catalog}
							<label class="field">
								<span>{t('corpus.search.label')}</span>
								<input type="search" bind:value={query} placeholder={t('corpus.search.ph')} autocomplete="off" />
								<span class="hint">{t('corpus.search.hint')}</span>
							</label>
							{#if searching}<p class="small muted" aria-live="polite">{t('common.loading')}</p>{/if}
							{#if results.length}
								<ul class="results" aria-label={t('corpus.search.results')}>
									{#each results as r (r.vbpl_id)}
										<li>
											<div class="result-main">
												<span class="serif">{r.title}</span>
												<span class="small muted">{[r.doc_type, r.doc_num, r.issue_date && formatDay(r.issue_date), r.agency].filter(Boolean).join(' · ')}</span>
												{#if r.effect_status}<span class="status {statusTone(r.effect_status)}" title={t('corpus.search.statusNote')}>{r.effect_status}*</span>{/if}
												{#if r.usually_no_articles}<span class="small no-articles"><Icon name="warn" size={14} />{t('corpus.search.noArticles')}</span>{/if}
											</div>
											{#if inCorpus.has(r.vbpl_id)}
												<span class="small muted added"><Icon name="check" size={16} />{t('corpus.search.inCorpus')}</span>
											{:else}
												<button type="button" class="btn small" disabled={busy || !listing?.vbpl_enabled} onclick={() => askFetch(r.vbpl_id, r.title)}>{t('corpus.fetch')}</button>
											{/if}
										</li>
									{/each}
								</ul>
								<p class="small muted">* {t('corpus.search.statusNote')}</p>
							{:else if query.trim().length >= 2 && !searching}
								<p class="small muted">{t('corpus.search.none')}</p>
							{/if}
						{:else}
							<p class="small muted">{t('research.catalog.missing')}</p>
						{/if}
					{:else if mode === 'link'}
						<form class="fields" onsubmit={(e) => { e.preventDefault(); askFetch(reference.trim(), reference.trim()); }}>
							<label class="field"><span>{t('corpus.link.label')}</span><input required bind:value={reference} placeholder="https://vbpl.vn/van-ban/chi-tiet/…" /><span class="hint">{t('corpus.link.hint')}</span></label>
							<label class="field"><span>{t('corpus.docId')} <span class="hint">({t('common.optional')})</span></span><input maxlength="80" bind:value={documentId} placeholder="45-2019-qh14" /><span class="hint">{t('corpus.docId.hint')}</span></label>
							<div><button class="btn primary" type="submit" disabled={busy || !listing?.vbpl_enabled}>{t('corpus.fetch')}</button></div>
						</form>
					{:else}
						<form class="fields" onsubmit={upload}>
							<label class="field"><span>{t('corpus.file.label')}</span><input type="file" accept={ACCEPT} required onchange={(e) => (file = (e.currentTarget as HTMLInputElement).files?.[0] ?? null)} /><span class="hint">{t('corpus.file.hint')}</span></label>
							<label class="field"><span>{t('corpus.file.title')} <span class="hint">({t('common.optional')})</span></span><input maxlength="200" bind:value={fileTitle} /></label>
							<label class="field"><span>{t('corpus.docId')} <span class="hint">({t('common.optional')})</span></span><input maxlength="80" bind:value={documentId} /><span class="hint">{t('corpus.docId.hint')}</span></label>
							<div><button class="btn primary" type="submit" disabled={busy || !file}><Icon name="upload" />{t('corpus.file.submit')}</button></div>
						</form>
					{/if}
				</section>

				<section class="panel" aria-labelledby="docs-heading">
					<h2 class="heading" id="docs-heading">{t('corpus.documents')}</h2>
					{#if corpus.documents.length}
						<ul class="docs">
							{#each corpus.documents as d (d.id)}
								<li>
									<div class="doc-main">
										<a class="serif" href="/research/{corpus.id}/document/{d.id}">{d.title}</a>
										<span class="small muted"><code>{d.document_id}</code> · {t('corpus.doc.counts', { articles: d.article_count, leaves: d.leaf_count })}</span>
										<span class="small muted">
											{#if d.source_kind === 'vbpl'}
												<a href={d.source_url} target="_blank" rel="noopener noreferrer">vbpl.vn</a> · {t('corpus.doc.accessed', { date: formatDay(d.accessed_at) })}
											{:else}
												{t('corpus.doc.file', { name: d.source_ref })}
											{/if}
										</span>
										<span class="tags">
											{#if d.metadata.effect_status?.name}<span class="status {statusTone(d.metadata.effect_status.name)}">{d.metadata.effect_status.name}</span>{/if}
											{#if d.audit_count}<a class="chip warn" href="/research/{corpus.id}/document/{d.id}#audit"><Icon name="warn" size={14} />{t('corpus.doc.audit', { n: d.audit_count })}</a>{/if}
											{#if d.warnings.includes('pdf_line_breaks')}<span class="chip warn">{t('corpus.doc.pdf')}</span>{/if}
										</span>
									</div>
									<button type="button" class="btn quiet small" onclick={() => remove(d)} aria-label={t('corpus.remove', { title: d.title })}><Icon name="x" size={16} /></button>
								</li>
							{/each}
						</ul>
					{:else}
						<p class="muted">{t('corpus.documents.empty')}</p>
					{/if}
				</section>
			</div>

			<section class="panel versions" aria-labelledby="versions-heading">
				<h2 class="heading" id="versions-heading">{t('corpus.versions')}</h2>
				<p class="small muted">{t('corpus.versions.lead')}</p>
				{#if corpus.changed_since_version && corpus.documents.length}
					<form class="fields" onsubmit={freeze}>
						<label class="field"><span>{t('corpus.freeze.note')} <span class="hint">({t('common.optional')})</span></span><input maxlength="500" bind:value={note} /></label>
						<div><button class="btn primary" type="submit" disabled={busy}><Icon name="lock" />{t('corpus.freeze')}</button></div>
					</form>
				{:else if corpus.documents.length}
					<p class="small">{t('corpus.freeze.unchanged')}</p>
				{/if}
				{#if corpus.versions.length}
					<ol class="timeline">
						{#each corpus.versions as v, i (v.id)}
							<li class:current={i === 0}>
								<p><strong>{t('corpus.version', { n: v.number })}</strong> · <span class="small">{formatDate(v.frozen_at)}</span></p>
								{#if v.note}<p class="small">{v.note}</p>{/if}
								<p class="small muted">{t('corpus.version.facts', { docs: v.document_count, units: v.unit_count, who: v.frozen_by })}</p>
								<p class="small muted">{t('corpus.version.id')}: <code>{v.id}</code> · SHA-256 <code title={v.bundle_sha256}>{v.bundle_sha256.slice(0, 12)}</code></p>
							</li>
						{/each}
					</ol>
				{/if}
			</section>
		</div>
	{/if}
</div>

<dialog bind:this={dialog} aria-labelledby="fetch-title" onclose={() => (pending = null)}>
	<h2 class="heading" id="fetch-title">{t('corpus.confirm.title')}</h2>
	<p>{t('corpus.confirm.body')}</p>
	{#if pending}<p class="serif target">{pending.label}</p>{/if}
	<p class="small muted">{t('corpus.confirm.note')}</p>
	<div class="row actions">
		<button type="button" class="btn quiet" onclick={() => dialog?.close()}>{t('common.cancel')}</button>
		<button type="button" class="btn primary" onclick={confirmFetch}><Icon name="globe" />{t('corpus.confirm.go')}</button>
	</div>
</dialog>

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
		grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr);
		gap: 20px;
		align-items: start;
	}
	.panel {
		display: grid;
		gap: 12px;
	}
	.segmented button {
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}
	.fields {
		display: grid;
		gap: 14px;
		max-width: 640px;
	}
	.results,
	.docs {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.results li,
	.docs li {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 16px;
		padding: 12px 0;
		border-top: 1px solid var(--rule);
	}
	.results li:first-child,
	.docs li:first-child {
		border-top: 0;
	}
	.result-main,
	.doc-main {
		display: grid;
		gap: 3px;
		min-width: 0;
	}
	.no-articles {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		color: var(--attention);
	}
	.added {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		white-space: nowrap;
		color: var(--approve);
	}
	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		margin-top: 4px;
	}
	.status {
		justify-self: start;
		font-size: 0.8rem;
		padding: 1px 8px;
		border-radius: 999px;
		border: 1px solid var(--rule);
		color: var(--ink-2);
	}
	.status.ok {
		background: var(--approve-soft);
		border-color: #b9dcc5;
		color: var(--approve);
	}
	.status.partial {
		background: var(--attention-soft);
		border-color: #f0d3a1;
		color: var(--attention);
	}
	.status.gone {
		background: var(--reject-soft);
		border-color: #f1c4bf;
		color: var(--reject);
	}
	.chip.warn {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		background: var(--attention-soft);
		color: var(--attention);
		border-color: #f0d3a1;
		text-decoration: none;
	}
	.timeline {
		list-style: none;
		margin: 4px 0 0;
		padding: 0 0 0 14px;
		border-left: 2px solid var(--rule);
		display: grid;
		gap: 14px;
	}
	.timeline li.current {
		border-left: 0;
	}
	.timeline p {
		margin: 0;
	}
	dialog {
		max-width: 520px;
		width: calc(100% - 32px);
		border: 1px solid var(--rule);
		border-radius: var(--r-panel);
		padding: 22px 24px;
		box-shadow: var(--shadow-pop);
		color: var(--ink);
	}
	dialog::backdrop {
		background: rgb(20 22 24 / 0.35);
	}
	dialog .target {
		font-size: 1.05rem;
		padding: 10px 12px;
		background: var(--desk);
		border-radius: var(--r-control);
	}
	.actions {
		justify-content: flex-end;
		gap: 10px;
		margin-top: 8px;
	}
	@media (max-width: 1000px) {
		.cols {
			grid-template-columns: 1fr;
		}
	}
</style>
