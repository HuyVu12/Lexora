<script lang="ts">
	import PageGuide from '#lib/components/PageGuide.svelte';
	import StepTag from '#lib/components/StepTag.svelte';
	import { goto } from '$app/navigation';
	import Icon from '#lib/components/Icon.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDay } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { act, notify } from '#lib/toast.svelte.js';
	import type { FrozenVersionOption, GoldSetSummary } from '#lib/types.js';

	let sets = $state<GoldSetSummary[] | null>(null);
	let versions = $state<FrozenVersionOption[]>([]);
	let name = $state('');
	let versionId = $state('');
	let sample = $state(20);
	let busy = $state(false);

	const load = () =>
		api<{ sets: GoldSetSummary[]; versions: FrozenVersionOption[] }>('/api/gold')
			.then((v) => {
				sets = v.sets;
				versions = v.versions;
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
				<p class="lead">{t('gold.lead')}</p>
			</div>
		</header>
		<PageGuide name="golds" steps={2} />

		<div class="cols">
			<section class="panel" aria-labelledby="sets-heading">
				<h2 class="heading" id="sets-heading"><StepTag n={2} />{t('gold.list')}</h2>
				{#if !sets}
					<p class="muted">{t('common.loading')}</p>
				{:else if sets.length}
					<ul class="sets">
						{#each sets as s (s.id)}
							<li>
								<a class="serif name" href="/research/gold/{s.id}">{s.name}</a>
								<p class="small muted">
									{t('gold.counts', { articles: s.articles, sentences: s.sentences })} · {t('qs.onVersion', { n: s.corpus_version })} ·
									{s.imported ? t('qs.importedFrom', { who: s.created_by }) : t('research.createdBy', { who: s.created_by, date: formatDay(s.created_at) })}
								</p>
								{#if Object.keys(s.labelled).length || s.adjudicated}
									<p class="small">
										{#each Object.entries(s.labelled) as [who, n] (who)}<span class="who">{t('gold.labelledBy', { who, n })}</span>{/each}
										{#if s.adjudicated}<span class="who">{t('gold.adjudicatedN', { n: s.adjudicated })}</span>{/if}
									</p>
								{/if}
							</li>
						{/each}
					</ul>
				{:else}
					<p class="muted">{t('gold.empty')}</p>
				{/if}
			</section>

			<div class="stack">
				<form class="panel" onsubmit={create}>
					<h2 class="heading"><StepTag n={1} />{t('gold.create')}</h2>
					{#if versions.length}
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

				<section class="panel">
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
		grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
		gap: 20px;
		align-items: start;
	}
	.panel {
		display: grid;
		gap: 12px;
	}
	.sets {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.sets li {
		display: grid;
		gap: 4px;
		justify-items: start;
		padding: 14px 0;
		border-top: 1px solid var(--rule);
	}
	.sets li:first-child {
		border-top: 0;
		padding-top: 4px;
	}
	.sets p {
		margin: 0;
	}
	.name {
		font-size: 1.15rem;
		font-weight: 600;
	}
	.who + .who::before {
		content: ' · ';
		color: var(--muted);
	}
	@media (max-width: 900px) {
		.cols {
			grid-template-columns: 1fr;
		}
	}
</style>
