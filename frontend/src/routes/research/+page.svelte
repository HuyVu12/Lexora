<script module lang="ts">
	import type { CorpusListing } from '#lib/types.js';
	// The last listing shows at once when you come back; a fresh one replaces it when it arrives.
	let last: CorpusListing | null = null;
</script>

<script lang="ts">
	import PageGuide from '#lib/components/PageGuide.svelte';
	import StepTag from '#lib/components/StepTag.svelte';
	import Skeleton from '#lib/components/Skeleton.svelte';
	import { goto } from '$app/navigation';
	import Icon from '#lib/components/Icon.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDay } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { act, notify } from '#lib/toast.svelte.js';
	import { revealItems } from '#lib/motion.js';
	import type { CorpusSummary } from '#lib/types.js';

	let listing = $state<CorpusListing | null>(last);
	const fresh = !last;
	let name = $state('');
	let description = $state('');
	let busy = $state(false);

	$effect(() => {
		if (!canReview(session.account)) return;
		api<CorpusListing>('/api/corpora')
			.then((v) => (listing = last = v))
			.catch((e) => notify(e.message, true));
	});

	const frozen = $derived(listing?.corpora.reduce((n, c) => n + (c.latest_version ?? 0), 0) ?? 0);

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
				<p class="facts">
					{#if listing}
						<span><strong>{listing.corpora.length}</strong> {t('research.facts.corpora', { n: listing.corpora.length })}</span>
						<span><strong>{frozen}</strong> {t('research.facts.versions', { n: frozen })}</span>
					{:else}
						{#each [80, 140] as w (w)}<span><Skeleton width="{w}px" height="12px" /></span>{/each}
					{/if}
				</p>
			</div>
		</header>
		<PageGuide name="corpora" steps={3} />

		<div class="cols">
			<section class="section" data-tour="corpus-list" aria-labelledby="corpora-heading" aria-busy={!listing}>
				<h2 class="subtitle" id="corpora-heading">{t('research.list')}</h2>
				{#if !listing}
					<span class="visually-hidden" role="status">{t('common.loading')}</span>
					<ul class="cards" aria-hidden="true">
						{#each [0, 1] as i (i)}
							<li class="panel card-row">
								<span class="body"><Skeleton width="44%" height="17px" /><Skeleton lines={2} height="11px" gap="8px" last="64%" /><Skeleton width="52%" height="11px" /></span>
							</li>
						{/each}
					</ul>
				{:else if listing.corpora.length}
					<ul class="cards" {@attach fresh && revealItems({ step: 40 })}>
						{#each listing.corpora as c (c.id)}
							<li>
								<a class="panel panel-link card-row" href="/research/{c.id}">
									<span class="body">
										<span class="name">{c.name}</span>
										{#if c.description}<span class="small desc">{c.description}</span>{/if}
										<span class="dotted">
											<span>{t('research.docs', { n: c.documents })}</span>
											<span>{t('research.createdBy', { who: c.created_by, date: formatDay(c.created_at) })}</span>
										</span>
									</span>
									<span class="side">
										{#if c.latest_version}
											<span class="chip"><Icon name="lock" size={13} />{t('research.latest', { n: c.latest_version })}</span>
										{:else}
											<span class="chip draft">{t('research.notFrozen')}</span>
										{/if}
									</span>
								</a>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="empty-note">{t('research.empty')}</p>
				{/if}
			</section>

			<form class="panel create" data-tour="corpus-create" onsubmit={create}>
				<h2 class="heading"><StepTag n={1} />{t('research.create')}</h2>
				<label class="field"><span>{t('research.name')}</span><input maxlength="120" required bind:value={name} placeholder={t('research.namePh')} /></label>
				<label class="field"><span>{t('research.description')} <span class="hint">({t('common.optional')})</span></span><textarea maxlength="2000" rows="3" bind:value={description}></textarea></label>
				<div><button class="btn primary" type="submit" disabled={busy}><Icon name="plus" />{t('research.createSubmit')}</button></div>
			</form>
		</div>
	{/if}
</div>

<style>
	.cols {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 380px;
		gap: var(--space-8);
		align-items: start;
	}
	.create {
		display: grid;
		gap: 12px;
		padding: 20px 22px;
	}
	.create .field textarea {
		min-height: 88px;
	}
	.desc {
		color: var(--ink-2);
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	.chip :global(svg) {
		flex: none;
	}
	.chip.draft {
		border-style: dashed;
		color: var(--muted);
	}
	@media (max-width: 960px) {
		.cols {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
