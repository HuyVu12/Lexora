<script module lang="ts">
	import type { FrozenVersionOption, GoldSetSummary } from '#lib/types.js';
	type Listing = { sets: GoldSetSummary[]; versions: FrozenVersionOption[] };
	// The last listing shows at once when you come back; a fresh one replaces it when it arrives.
	let last: Listing | null = null;
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

	let data = $state<Listing | null>(last);
	const fresh = !last;
	let name = $state('');
	let versionId = $state(last?.versions[0]?.id ?? '');
	let sample = $state(20);
	let busy = $state(false);

	const sets = $derived(data?.sets ?? null);
	const versions = $derived(data?.versions ?? []);
	const me = $derived(session.account?.username ?? '');
	const mine = (s: GoldSetSummary) => s.labelled[me] ?? 0;
	const sentences = $derived(sets?.reduce((n, s) => n + s.sentences, 0) ?? 0);
	const labelled = $derived(sets?.reduce((n, s) => n + mine(s), 0) ?? 0);

	const load = () =>
		api<Listing>('/api/gold')
			.then((v) => {
				data = last = v;
				versionId ||= v.versions[0]?.id ?? '';
			})
			.catch((e) => notify(e.message, true));

	$effect(() => {
		if (canReview(session.account)) load();
	});

	async function create(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		await act(async () => {
			const made = await api<GoldSetSummary>('/api/gold', { name, corpus_version_id: versionId, sample });
			await goto(`/research/gold/${made.id}`);
		});
		busy = false;
	}

	async function importPack(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		busy = true;
		await act(async () => {
			const made = await api<GoldSetSummary>('/api/gold/import-pack', { pack: JSON.parse(await file.text()) });
			notify({ key: 'gold.imported', params: { name: made.name } });
			await load();
		});
		input.value = '';
		busy = false;
	}
</script>

<svelte:head><title>{t('gold.title')} · Lexora</title></svelte:head>

<div class="page">
	{#if !canReview(session.account)}
		<h1 class="title">{t('common.forbidden.title')}</h1>
		<p class="lead">{t('common.forbidden.body')}</p>
	{:else}
		<header class="page-head">
			<div>
				<h1 class="title">{t('gold.title')}</h1>
				<p class="facts">
					{#if sets}
						<span><strong>{sets.length}</strong> {t('gold.facts.sets', { n: sets.length })}</span>
						<span>{t('gold.facts.mine', { done: labelled, n: sentences })}</span>
					{:else}
						{#each [90, 170] as w (w)}<span><Skeleton width="{w}px" height="12px" /></span>{/each}
					{/if}
				</p>
			</div>
		</header>
		<PageGuide name="golds" steps={2} />

		<div class="cols">
			<section class="section" aria-labelledby="sets-heading" aria-busy={!sets}>
				<h2 class="subtitle" id="sets-heading"><StepTag n={2} />{t('gold.list')}</h2>
				{#if !sets}
					<span class="visually-hidden" role="status">{t('common.loading')}</span>
					<ul class="cards" aria-hidden="true">
						{#each [0, 1] as i (i)}
							<li class="panel card-row">
								<span class="body"><Skeleton width="46%" height="17px" /><Skeleton width="72%" height="11px" /><Skeleton width="38%" height="11px" /></span>
								<span class="side"><Skeleton width="120px" height="11px" /><Skeleton width="120px" height="6px" radius="3px" /></span>
							</li>
						{/each}
					</ul>
				{:else if sets.length}
					<ul class="cards" {@attach fresh && revealItems({ step: 40 })}>
						{#each sets as s (s.id)}
							<li>
								<a class="panel panel-link card-row" href="/research/gold/{s.id}">
									<span class="body">
										<span class="name">{s.name}</span>
										<span class="dotted">
											<span>{t('gold.counts', { articles: s.articles, sentences: s.sentences })}</span>
											{#if s.sample_size}<span>{t('gold.sampleFacts', { articles: s.sample_size.articles, sentences: s.sample_size.sentences })}</span>{/if}
											<span>{t('qs.onVersion', { n: s.corpus_version })}</span>
										</span>
										<span class="dotted">
											<span>{s.imported ? t('qs.importedFrom', { who: s.created_by }) : t('research.createdBy', { who: s.created_by, date: formatDay(s.created_at) })}</span>
											{#each Object.entries(s.labelled).filter(([who]) => who !== me) as [who, n] (who)}<span>{t('gold.labelledBy', { who, n })}</span>{/each}
											{#if s.adjudicated}<span>{t('gold.adjudicatedN', { n: s.adjudicated })}</span>{/if}
										</span>
									</span>
									<span class="side progress">
										<span class="small">{t('gold.facts.mine', { done: mine(s), n: s.sentences })}</span>
										<span class="meter" aria-hidden="true"><i style:transform="scaleX({s.sentences ? Math.min(mine(s), s.sentences) / s.sentences : 0})"></i></span>
									</span>
								</a>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="empty-note">{t('gold.empty')}</p>
				{/if}
			</section>

			<div class="side-stack">
				<form class="panel form" onsubmit={create}>
					<h2 class="heading"><StepTag n={1} />{t('gold.create')}</h2>
					{#if !data}
						<Skeleton lines={3} height="38px" gap="14px" last="100%" />
					{:else if versions.length}
						<label class="field"><span>{t('gold.name')}</span><input maxlength="120" required bind:value={name} placeholder={t('gold.namePh')} /></label>
						<label class="field"><span>{t('gold.version')}</span>
							<select bind:value={versionId}>
								{#each versions as v (v.id)}<option value={v.id}>{v.corpus_name} · {t('corpus.version', { n: v.number })} ({t('research.docs', { n: v.document_count })})</option>{/each}
							</select>
						</label>
						<label class="field"><span>{t('gold.sample')}</span>
							<input type="number" min="1" max="120" required bind:value={sample} />
							<span class="hint">{t('gold.sampleHint')}</span>
						</label>
						<div><button class="btn primary" type="submit" disabled={busy}><Icon name="plus" />{t('gold.createSubmit')}</button></div>
					{:else}
						<p class="small">{t('gold.noVersion')} <a href="/research">{t('research.title')}</a></p>
					{/if}
				</form>

				<section class="panel form">
					<h2 class="heading"><StepTag n={1} />{t('gold.importPack')}</h2>
					<p class="small muted">{t('gold.importPackLead')}</p>
					<label class="field"><span>{t('gold.packFile')}</span><input type="file" accept=".json,application/json" disabled={busy} onchange={importPack} /></label>
				</section>
			</div>
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
	.side-stack {
		display: grid;
		gap: var(--space-4);
	}
	.form {
		display: grid;
		gap: 12px;
		padding: 20px 22px;
	}
	.progress {
		min-width: 150px;
	}
	.progress .meter {
		width: 150px;
	}
	@media (max-width: 960px) {
		.cols {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	@media (max-width: 640px) {
		.progress .meter {
			width: 100%;
		}
		.progress {
			width: 100%;
		}
	}
</style>
