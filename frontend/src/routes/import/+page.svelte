<script lang="ts">
	import PageGuide from '#lib/components/PageGuide.svelte';
	import StepTag from '#lib/components/StepTag.svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import Steps from '#lib/components/Steps.svelte';
	import Term from '#lib/components/Term.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDay } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { notify, act } from '#lib/toast.svelte.js';
	import type { AppState, SourceEntry } from '#lib/types.js';

	let app = $state<AppState | null>(null);
	let sources = $state<SourceEntry[]>([]);
	let source = $state<'library' | 'file' | 'paste'>('file');
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
		Promise.all([api<AppState>('/api/state'), api<{ entries: SourceEntry[] }>('/api/sources')])
			.then(([s, lib]) => {
				app = s;
				sources = lib.entries;
				if (sources.length) {
					source = 'library';
					sourceId = sources[0].id;
				}
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

	async function readFile(event: Event) {
		const file = (event.currentTarget as HTMLInputElement).files?.[0];
		if (!file) return;
		if (!file.name.toLowerCase().endsWith('.txt') || file.size > 1_000_000) return notify({ key: 'import.fileError' }, true);
		try {
			text = new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer());
			title ||= file.name.replace(/\.txt$/i, '');
			notify({ key: 'import.fileRead' });
		} catch {
			notify({ key: 'import.fileError' }, true);
		}
	}

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		await act(async () => {
			const target = mode === 'new' ? { mode: 'new', name, description, data_class: dataClass } : { mode: 'merge', kb_id: kbId };
			const made =
				source === 'library'
					? await api<{ id: string }>('/api/prepare-source', { source_id: sourceId, target, extraction })
					: await api<{ id: string }>('/api/prepare', { title, text, synthetic, target, extraction });
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
					{#if sources.length}
						<label class="choice"><input type="radio" name="source" value="library" bind:group={source} /><strong>{t('import.source.library')}</strong><span>{t('import.source.libraryHint')}</span></label>
					{/if}
					<label class="choice"><input type="radio" name="source" value="file" bind:group={source} /><strong>{t('import.source.file')}</strong><span>{t('import.source.fileHint')}</span></label>
					<label class="choice"><input type="radio" name="source" value="paste" bind:group={source} /><strong>{t('import.source.paste')}</strong><span>{t('import.source.pasteHint')}</span></label>
				</div>
				{#if source === 'library'}
					<div class="sources">
						{#each sources as s (s.id)}
							<label class="choice"><input type="radio" name="libsrc" value={s.id} bind:group={sourceId} /><strong class="serif">{s.title}</strong><span>{t('import.downloaded', { date: formatDay(s.downloaded_at) })}</span></label>
						{/each}
					</div>
				{:else}
					<div class="fields">
						{#if source === 'file'}
							<label class="field"><span>{t('import.file')}</span><input type="file" accept=".txt,text/plain" onchange={readFile} /><span class="hint">{t('import.fileHelp')}</span></label>
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
				<button class="btn primary" type="submit" disabled={busy}><StepTag n={4} compact />{t('import.submit')}</button>
				<span class="small muted">{extraction === 'llm' ? t('import.method.aiNote') : t('import.method.rulesNote')}</span>
			</div>
		</form>
	{/if}
</div>

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
	.submit {
		gap: 14px;
	}
	.submit .btn {
		min-height: 44px;
		padding: 0 22px;
	}
</style>
