<script lang="ts">
	import { goto } from '$app/navigation';
	import Icon from '#lib/components/Icon.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDay } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { act, notify } from '#lib/toast.svelte.js';
	import type { CorpusListing, CorpusSummary } from '#lib/types.js';

	let listing = $state<CorpusListing | null>(null);
	let name = $state('');
	let description = $state('');
	let busy = $state(false);

	$effect(() => {
		if (!canReview(session.account)) return;
		api<CorpusListing>('/api/corpora')
			.then((v) => (listing = v))
			.catch((e) => notify(e.message, true));
	});

	async function create(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		await act(async () => {
			const made = await api<CorpusSummary>('/api/corpora', { name, description });
			await goto(`/research/${made.id}`);
		});
		busy = false;
	}
</script>

<svelte:head><title>{t('research.title')} · Lexora</title></svelte:head>

<div class="page">
	{#if !canReview(session.account)}
		<h1 class="title">{t('common.forbidden.title')}</h1>
		<p class="lead">{t('common.forbidden.body')}</p>
	{:else}
		<header class="page-head">
			<div>
				<h1 class="title">{t('research.title')}</h1>
				<p class="lead">{t('research.lead')}</p>
			</div>
		</header>

		{#if listing}
			<ul class="status">
				<li>
					<Icon name="search" />
					{#if listing.catalog}
						<span>{t('research.catalog.ready', { n: listing.catalog.documents.toLocaleString('vi-VN') })}</span>
					{:else}
						<span>{t('research.catalog.missing')}</span>
					{/if}
				</li>
				<li>
					<Icon name="globe" />
					<span>{listing.vbpl_enabled ? t('research.vbpl.on') : t('research.vbpl.off')}</span>
				</li>
			</ul>
		{/if}

		<div class="cols">
			<section class="panel" aria-labelledby="corpora-heading">
				<h2 class="heading" id="corpora-heading">{t('research.list')}</h2>
				{#if !listing}
					<p class="muted">{t('common.loading')}</p>
				{:else if listing.corpora.length}
					<ul class="corpora">
						{#each listing.corpora as c (c.id)}
							<li>
								<a class="serif name" href="/research/{c.id}">{c.name}</a>
								{#if c.description}<p class="small">{c.description}</p>{/if}
								<p class="small muted">
									{t('research.docs', { n: c.documents })} ·
									{c.latest_version ? t('research.latest', { n: c.latest_version }) : t('research.notFrozen')} ·
									{t('research.createdBy', { who: c.created_by, date: formatDay(c.created_at) })}
								</p>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="muted">{t('research.empty')}</p>
				{/if}
			</section>

			<form class="panel create" onsubmit={create}>
				<h2 class="heading">{t('research.create')}</h2>
				<p class="small muted">{t('research.createLead')}</p>
				<label class="field"><span>{t('research.name')}</span><input maxlength="120" required bind:value={name} placeholder={t('research.namePh')} /></label>
				<label class="field"><span>{t('research.description')} <span class="hint">({t('common.optional')})</span></span><textarea maxlength="2000" rows="3" bind:value={description}></textarea></label>
				<div><button class="btn primary" type="submit" disabled={busy}><Icon name="plus" />{t('research.createSubmit')}</button></div>
			</form>
		</div>
	{/if}
</div>

<style>
	.status {
		list-style: none;
		margin: 0 0 20px;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		gap: 8px 24px;
		color: var(--ink-2);
	}
	.status li {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.cols {
		display: grid;
		grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
		gap: 20px;
		align-items: start;
	}
	.panel {
		display: grid;
		gap: 12px;
	}
	.corpora {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.corpora li {
		padding: 14px 0;
		border-top: 1px solid var(--rule);
		display: grid;
		gap: 4px;
	}
	.corpora li:first-child {
		border-top: 0;
		padding-top: 4px;
	}
	.name {
		font-size: 1.15rem;
		font-weight: 600;
	}
	@media (max-width: 900px) {
		.cols {
			grid-template-columns: 1fr;
		}
	}
</style>
