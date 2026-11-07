<script lang="ts">
	import PageGuide from '#lib/components/PageGuide.svelte';
	import StepTag from '#lib/components/StepTag.svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import Steps from '#lib/components/Steps.svelte';
	import Term from '#lib/components/Term.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import CatalogSearch from '#lib/components/CatalogSearch.svelte';
	import ArticlePicker from '#lib/components/ArticlePicker.svelte';
	import ConfirmDialog from '#lib/components/ConfirmDialog.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDay } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { notify, act } from '#lib/toast.svelte.js';
	import type { AppState, CatalogEntry, CorpusListing, SourceEntry, VbplImport } from '#lib/types.js';

	const ACCEPT = '.txt,.html,.htm,.docx,.pdf';
	const MAX_FILE = 20_000_000;
	const MAX_ARTICLES = 60;

	let app = $state<AppState | null>(null);
	let sources = $state<SourceEntry[]>([]);
	let source = $state<'library' | 'catalog' | 'link' | 'file' | 'paste'>('file');
	let listing = $state<CorpusListing | null>(null);
	let reference = $state('');
	let fetched = $state<VbplImport | null>(null);
	let chosen = $state<string[]>([]);
	let file = $state<File | null>(null);
	let confirmOpen = $state(false);
	let pending = $state<{ reference: string; label: string } | null>(null);
	let sourceId = $state('');
	let title = $state('');
	let text = $state('');
	let synthetic = $state(false);
	let mode = $state<'new' | 'merge'>('new');
	let kbId = $state('');
	let name = $state('');
	let description = $state('');
	let dataClass = $state<'private' | 'public'>('private');
	let extraction = $state<'rules' | 'llm'>('rules');
	let busy = $state(false);

	$effect(() => {
		if (!canReview(session.account)) return;
		Promise.all([api<AppState>('/api/state'), api<{ entries: SourceEntry[] }>('/api/sources'), api<CorpusListing>('/api/corpora')])
			.then(([s, lib, corpora]) => {
				app = s;
				sources = lib.entries;
				listing = corpora;
				if (corpora.catalog && corpora.vbpl_enabled) source = 'catalog';
				else if (sources.length) source = 'library';
				if (sources.length) sourceId = sources[0].id;
				const preset = page.url.searchParams.get('kb');
				if (preset && s.knowledge_bases.some((k) => k.id === preset)) {
					mode = 'merge';
					kbId = preset;
				} else kbId = s.knowledge_bases[0]?.id ?? '';
			})
			.catch((e) => notify(e.message, true));
	});

	const kbs = $derived(app?.knowledge_bases ?? []);
	const targetPublic = $derived(mode === 'new' ? dataClass === 'public' : kbs.find((k) => k.id === kbId)?.data_class === 'public');
	const aiAllowed = $derived(!!app?.extraction_model && targetPublic);
	$effect(() => {
		if (!aiAllowed) extraction = 'rules';
	});

	function pickFile(event: Event) {
		file = (event.currentTarget as HTMLInputElement).files?.[0] ?? null;
		if (file && file.size > MAX_FILE) {
			notify({ key: 'corpus.file.tooBig' }, true);
			file = null;
		}
		if (file && !title) title = file.name.replace(/\.[^.]+$/, '');
	}

	function toBase64(buffer: ArrayBuffer) {
		const bytes = new Uint8Array(buffer);
		let binary = '';
		for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
		return btoa(binary);
	}

	// vbpl.vn: one confirmed fetch returns the article outline; the draft is cut from the chosen articles.
	function askFetch(ref: string, label: string) {
		pending = { reference: ref, label };
		confirmOpen = true;
	}
	async function fetchDocument() {
		if (!pending) return;
		const ref = pending.reference;
		busy = true;
		await act(async () => {
			fetched = await api<VbplImport>('/api/import/vbpl', { reference: ref, confirm: true });
			chosen = [];
		});
		busy = false;
		pending = null;
	}
	const ready = $derived(
		source === 'catalog' || source === 'link'
			? !!fetched && chosen.length > 0 && chosen.length <= MAX_ARTICLES
			: source === 'file'
				? !!file && !!title.trim()
				: true
	);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		await act(async () => {
			const target = mode === 'new' ? { mode: 'new', name, description, data_class: dataClass } : { mode: 'merge', kb_id: kbId };
			let made: { id: string };
			if (source === 'library') made = await api('/api/prepare-source', { source_id: sourceId, target, extraction });
			else if (source === 'catalog' || source === 'link')
				made = await api('/api/prepare-vbpl', { vbpl_id: fetched!.vbpl_id, source_sha256: fetched!.source_sha256, article_ids: chosen, target, extraction });
			else if (source === 'file')
				made = await api('/api/prepare-file', { filename: file!.name, content_base64: toBase64(await file!.arrayBuffer()), title, synthetic, target, extraction });
			else made = await api('/api/prepare', { title, text, synthetic, target, extraction });
			await goto(`/drafts/${made.id}`);
		});
		busy = false;
	}
</script>

<svelte:head><title>{t('import.title')} · Lexora</title></svelte:head>

<div class="page narrow">
	{#if !canReview(session.account)}
		<h1 class="title">{t('common.forbidden.title')}</h1>
		<p class="lead">{t('common.forbidden.body')}</p>
	{:else}
		<Steps current={1} />
		<header class="page-head">
			<div>
				<h1 class="title">{t('import.title')}</h1>
				<p class="lead">{t('import.lead')}</p>
			</div>
		</header>
		<PageGuide name="import" steps={4} />

		<form class="stack" onsubmit={submit}>
			<fieldset class="panel">
				<legend class="heading"><StepTag n={1} />{t('import.source.title')}</legend>
				<p class="small muted">{t('import.source.lead')}</p>
				<div class="choices">
					{#if listing?.catalog}
						<label class="choice"><input type="radio" name="source" value="catalog" bind:group={source} /><strong>{t('import.source.catalog')}</strong><span>{t('import.source.catalogHint')}</span></label>
					{/if}
					{#if listing?.vbpl_enabled}
						<label class="choice"><input type="radio" name="source" value="link" bind:group={source} /><strong>{t('import.source.link')}</strong><span>{t('import.source.linkHint')}</span></label>
					{/if}
					{#if sources.length}
						<label class="choice"><input type="radio" name="source" value="library" bind:group={source} /><strong>{t('import.source.library')}</strong><span>{t('import.source.libraryHint')}</span></label>
					{/if}
					<label class="choice"><input type="radio" name="source" value="file" bind:group={source} /><strong>{t('import.source.file')}</strong><span>{t('import.source.fileHint')}</span></label>
					<label class="choice"><input type="radio" name="source" value="paste" bind:group={source} /><strong>{t('import.source.paste')}</strong><span>{t('import.source.pasteHint')}</span></label>
				</div>
				{#if source === 'catalog' || source === 'link'}
					{#if !listing?.vbpl_enabled}<p class="notice warn small">{t('research.vbpl.off')}</p>{/if}
					{#if fetched}
						<div class="fetched">
							<div>
								<p class="serif doc-title">{fetched.metadata.title}</p>
								<p class="small muted">
									{[fetched.metadata.doc_type, fetched.metadata.doc_num, fetched.metadata.effect_status?.name].filter(Boolean).join(' · ')} ·
									<a href={fetched.site_url} target="_blank" rel="noopener noreferrer">vbpl.vn</a> · {t('corpus.doc.accessed', { date: formatDay(fetched.accessed_at) })}
								</p>
							</div>
							<button type="button" class="btn quiet small" onclick={() => { fetched = null; chosen = []; }}>{t('import.pick.other')}</button>
						</div>
						<p class="small">{t('import.pick.lead')}</p>
						<ArticlePicker articles={fetched.articles} bind:selected={chosen} max={MAX_ARTICLES} />
					{:else if source === 'catalog'}
						<CatalogSearch canFetch={!!listing?.vbpl_enabled} {busy} onpick={(r: CatalogEntry) => askFetch(r.vbpl_id, r.title)} />
					{:else}
						<div class="fields">
							<label class="field"><span>{t('corpus.link.label')}</span><input bind:value={reference} placeholder="https://vbpl.vn/van-ban/chi-tiet/…" /><span class="hint">{t('corpus.link.hint')}</span></label>
							<div><button type="button" class="btn" disabled={busy || !reference.trim() || !listing?.vbpl_enabled} onclick={() => askFetch(reference.trim(), reference.trim())}><Icon name="globe" />{t('corpus.fetch')}</button></div>
						</div>
					{/if}
				{:else if source === 'library'}
					<div class="sources">
						{#each sources as s (s.id)}
							<label class="choice"><input type="radio" name="libsrc" value={s.id} bind:group={sourceId} /><strong class="serif">{s.title}</strong><span>{t('import.downloaded', { date: formatDay(s.downloaded_at) })}</span></label>
						{/each}
					</div>
				{:else}
					<div class="fields">
						{#if source === 'file'}
							<label class="field"><span>{t('import.file')}</span><input type="file" accept={ACCEPT} onchange={pickFile} /><span class="hint">{t('import.fileHelp')}</span></label>
						{/if}
						<label class="field"><span>{t('import.docTitle')}</span><input maxlength="200" required bind:value={title} /></label>
						{#if source === 'paste'}
							<label class="field"><span>{t('import.content')}</span><textarea required placeholder={t('import.contentPh')} bind:value={text}></textarea></label>
						{/if}
						<label class="check"><input type="checkbox" bind:checked={synthetic} />{t('import.synthetic')}</label>
					</div>
				{/if}
			</fieldset>

			<fieldset class="panel">
				<legend class="heading"><StepTag n={2} />{t('import.target.title')}</legend>
				<p class="small muted">{t('import.target.lead')}</p>
				<div class="choices">
					<label class="choice"><input type="radio" name="target" value="new" bind:group={mode} /><strong>{t('import.target.new')}</strong><span>{t('import.target.newHint')}</span></label>
					<label class="choice"><input type="radio" name="target" value="merge" bind:group={mode} disabled={!kbs.length} /><strong>{t('import.target.merge')}</strong><span>{kbs.length ? t('import.target.mergeHint') : t('import.target.mergeNone')}</span></label>
				</div>
				<div class="fields">
					{#if mode === 'new'}
						<label class="field"><span>{t('import.kbName')}</span><input maxlength="100" required placeholder={t('import.kbNamePh')} bind:value={name} /></label>
						<label class="field"><span>{t('import.kbDesc')} <span class="hint">({t('common.optional')})</span></span><input maxlength="500" bind:value={description} /></label>
						<div class="choices">
							<label class="choice"><input type="radio" name="dataclass" value="private" bind:group={dataClass} /><strong><Term key="private" focusable={false}>{t('import.private')}</Term></strong><span>{t('import.privateHint')}</span></label>
							<label class="choice"><input type="radio" name="dataclass" value="public" bind:group={dataClass} /><strong><Term key="public" focusable={false}>{t('import.public')}</Term></strong><span>{t('import.publicHint')}</span></label>
						</div>
					{:else}
						<label class="field"><span>{t('import.target.kb')}</span>
							<select bind:value={kbId}>{#each kbs as k (k.id)}<option value={k.id}>{k.name} ({t('home.kb.docs', { n: k.documents })})</option>{/each}</select>
						</label>
						<p class="small muted">{t('import.target.preview')}</p>
					{/if}
				</div>
			</fieldset>

			<fieldset class="panel">
				<legend class="heading"><StepTag n={3} />{t('import.method.title')}</legend>
				<p class="small muted">{t('import.method.lead')}</p>
				<div class="choices">
					<label class="choice"><input type="radio" name="method" value="rules" bind:group={extraction} /><strong>{t('import.method.rules')}</strong><span>{t('import.method.rulesHint')}</span></label>
					{#if app?.extraction_model}
						<label class="choice"><input type="radio" name="method" value="llm" bind:group={extraction} disabled={!aiAllowed} /><strong><Term key="ai" focusable={false}>{t('import.method.ai')}</Term></strong><span>{targetPublic ? t('import.method.aiHint', { model: app.extraction_model }) : t('import.method.aiPrivate')}</span></label>
					{/if}
				</div>
			</fieldset>

			<div class="row submit">
				<button class="btn primary" type="submit" disabled={busy || !ready}><StepTag n={4} compact />{t('import.submit')}</button>
				<span class="small muted">{extraction === 'llm' ? t('import.method.aiNote') : t('import.method.rulesNote')}</span>
			</div>
		</form>
	{/if}
</div>

<ConfirmDialog bind:open={confirmOpen} title={t('corpus.confirm.title')} confirmLabel={t('corpus.confirm.go')} onconfirm={fetchDocument}>
	<p>{t('corpus.confirm.body')}</p>
	{#if pending}<p class="serif confirm-target">{pending.label}</p>{/if}
	<p class="small muted">{t('corpus.confirm.note')}</p>
</ConfirmDialog>

<style>
	.narrow {
		max-width: 920px;
	}
	fieldset {
		margin: 0;
		display: grid;
		gap: 12px;
	}
	legend {
		padding: 0;
		float: left;
		width: 100%;
	}
	.sources,
	.fields {
		display: grid;
		gap: 14px;
		max-width: 640px;
	}
	.sources {
		max-width: none;
	}
	.fetched {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 12px;
		padding: 12px 14px;
		border: 1px solid var(--rule);
		border-radius: var(--r-control);
		background: var(--paper);
	}
	.fetched p {
		margin: 0;
	}
	.doc-title {
		font-size: 1.1rem;
		font-weight: 600;
	}
	.confirm-target {
		font-size: 1.05rem;
		padding: 10px 12px;
		background: var(--desk);
		border-radius: var(--r-control);
	}
	.submit {
		gap: 14px;
	}
	.submit .btn {
		min-height: 44px;
		padding: 0 22px;
	}
</style>
