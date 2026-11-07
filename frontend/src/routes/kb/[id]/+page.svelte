<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import Icon from '#lib/components/Icon.svelte';
	import Term from '#lib/components/Term.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDate } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { act } from '#lib/toast.svelte.js';
	import type { KbDetail } from '#lib/types.js';

	let kb = $state<KbDetail | null>(null);
	let error = $state('');
	const id = $derived(page.params.id ?? '');
	const published = $derived(page.url.searchParams.get('published') === '1');

	$effect(() => {
		void id;
		kb = null;
		api<KbDetail>(`/api/kb?id=${encodeURIComponent(id)}`).then((v) => (kb = v)).catch((e) => (error = e.message));
	});

	const startChat = () =>
		act(async () => {
			const created = await api<{ id: string }>('/api/chat/start', { kb_ids: [id] });
			await goto(`/chat/${created.id}`);
		});
</script>

<svelte:head><title>{kb?.name ?? t('nav.kbs')} · Lexora</title></svelte:head>

<div class="page">
	{#if error}
		<p class="notice error" role="alert">{error}</p>
	{:else if !kb}
		<p class="muted">{t('common.loading')}</p>
	{:else}
		{#if published}<p class="notice info published" role="status">{t('kb.published')}</p>{/if}
		<header class="page-head">
			<div>
				<h1 class="title">{kb.name}</h1>
				{#if kb.description}<p class="lead">{kb.description}</p>{/if}
				<p class="facts">
					<span>{t('home.kb.docs', { n: kb.documents.length })}</span>
					<span><Term key="approved">{t('home.kb.norms', { n: kb.approved_claims })}</Term></span>
					<span><Term key="revision">{t('kb.revisions', { n: kb.revisions.length })}</Term></span>
					<span class="chip {kb.data_class}"><Term key={kb.data_class}>{kb.data_class === 'private' ? t('kb.private') : t('kb.public')}</Term></span>
				</p>
			</div>
			<div class="row">
				<a class="btn" href="/kb/{kb.id}/graph"><Icon name="graph" />{t('kb.graph')}</a>
				{#if canReview(session.account)}<a class="btn" href="/import?kb={kb.id}"><Icon name="upload" />{t('kb.importInto')}</a>{/if}
				<button type="button" class="btn primary" disabled={!kb.approved_claims} onclick={startChat}><Icon name="chat" />{t('kb.ask')}</button>
			</div>
		</header>



		<div class="cols">
			<section class="panel">
				<h2 class="heading">{t('kb.documents')}</h2>
				<p class="small muted">{t('kb.documents.validity')}</p>
				{#if kb.documents.length}
					<ul class="docs">
						{#each kb.documents as d, i (i)}
							<li>
								<span class="docicon"><Icon name="doc" /></span>
								<span class="docname"><span class="serif">{d.title}</span>{#if d.synthetic}<span class="chip synthetic">{t('common.synthetic')}</span>{/if}</span>
								{#if /^https:\/\//.test(d.source_url)}<a href={d.source_url} target="_blank" rel="noopener noreferrer">{t('kb.source')}</a>{:else}<span class="small muted">{t('kb.uploaded')}</span>{/if}
							</li>
						{/each}
					</ul>
				{:else}<p class="muted">{t('kb.documents.empty')}</p>{/if}
			</section>
			<section class="panel">
				<h2 class="heading">{t('kb.history')}</h2>
				<p class="small muted">{t('kb.history.lead')}</p>
				<ol class="timeline">
					{#each kb.revisions as r, i (r.id)}
						<li class:current={i === 0}>
							<p><strong>{formatDate(r.created_at)}</strong>{#if i === 0}<span class="chip dark">{t('kb.current')}</span>{/if}</p>
							<p class="small">{r.reviewer ? `${r.reviewer}: ${r.reason}` : r.reason}</p>
							<p class="small muted">{t('kb.revisionId')}: <code>{r.id}</code></p>
						</li>
					{/each}
				</ol>
			</section>
		</div>
	{/if}
</div>

<style>
	.published {
		margin-bottom: 20px;
	}
	.facts {
		display: flex;
		flex-wrap: wrap;
		gap: 6px 18px;
		align-items: center;
		margin-top: 10px;
		color: var(--ink-2);
	}
	.cols {
		display: grid;
		grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr);
		gap: 20px;
		align-items: start;
	}
	.panel {
		display: grid;
		gap: 8px;
	}
	.docs {
		list-style: none;
		margin: 8px 0 0;
		padding: 0;
	}
	.docs li {
		display: grid;
		grid-template-columns: 34px minmax(0, 1fr) auto;
		gap: 12px;
		align-items: center;
		padding: 12px 0;
		border-top: 1px solid var(--rule);
	}
	.docicon {
		width: 34px;
		height: 34px;
		border-radius: 8px;
		display: grid;
		place-items: center;
		background: var(--desk);
	}
	.docname {
		display: flex;
		gap: 8px;
		align-items: center;
		flex-wrap: wrap;
		font-size: 16px;
	}
	.timeline {
		list-style: none;
		margin: 8px 0 0;
		padding: 0;
	}
	.timeline li {
		position: relative;
		padding: 0 0 18px 24px;
		display: grid;
		gap: 2px;
	}
	.timeline li::before {
		content: '';
		position: absolute;
		left: 4px;
		top: 7px;
		width: 9px;
		height: 9px;
		border-radius: 50%;
		background: var(--rule-strong);
	}
	.timeline li.current::before {
		background: var(--graphite);
		box-shadow: 0 0 0 3px var(--desk-2);
	}
	.timeline li:not(:last-child)::after {
		content: '';
		position: absolute;
		left: 8px;
		top: 18px;
		bottom: 0;
		width: 1px;
		background: var(--rule);
	}
	.timeline .chip {
		margin-left: 8px;
	}
	code {
		font-size: 12.5px;
		overflow-wrap: anywhere;
	}
	@media (max-width: 900px) {
		.cols {
			grid-template-columns: 1fr;
		}
	}
</style>
