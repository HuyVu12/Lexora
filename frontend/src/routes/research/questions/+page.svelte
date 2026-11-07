<script lang="ts">
	import PageGuide from '#lib/components/PageGuide.svelte';
	import StepTag from '#lib/components/StepTag.svelte';
	import { goto } from '$app/navigation';
	import Icon from '#lib/components/Icon.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDay } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { act, notify } from '#lib/toast.svelte.js';
	import type { FrozenVersionOption, QuestionSetSummary } from '#lib/types.js';

	let sets = $state<QuestionSetSummary[] | null>(null);
	let versions = $state<FrozenVersionOption[]>([]);
	let model = $state<string | null>(null);
	let name = $state('');
	let versionId = $state('');
	let guideline = $state('');
	let busy = $state(false);

	const load = () =>
		api<{ sets: QuestionSetSummary[]; versions: FrozenVersionOption[]; proposal_model: string | null }>('/api/question-sets')
			.then((v) => {
				sets = v.sets;
				versions = v.versions;
				model = v.proposal_model;
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
			const made = await api<QuestionSetSummary>('/api/question-sets', { name, corpus_version_id: versionId, guideline });
			await goto(`/research/questions/${made.id}`);
		});
		busy = false;
	}

	async function importPack(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		busy = true;
		await act(async () => {
			const pack = JSON.parse(await file.text());
			const made = await api<QuestionSetSummary>('/api/question-sets/import-pack', { pack });
			notify({ key: 'qs.imported', params: { name: made.name } });
			await load();
		});
		input.value = '';
		busy = false;
	}
</script>

<svelte:head><title>{t('qs.title')} · Lexora</title></svelte:head>

<div class="page">
	{#if !canReview(session.account)}
		<h1 class="title">{t('common.forbidden.title')}</h1>
		<p class="lead">{t('common.forbidden.body')}</p>
	{:else}
		<header class="page-head">
			<div>
				<h1 class="title">{t('qs.title')}</h1>
				<p class="lead">{t('qs.lead')}</p>
			</div>
		</header>
		<PageGuide name="qsets" steps={2} />
		<p class="status"><Icon name="info" />{model ? t('qs.model.on', { model }) : t('qs.model.off')}</p>

		<div class="cols">
			<section class="panel" aria-labelledby="sets-heading">
				<h2 class="heading" id="sets-heading"><StepTag n={2} />{t('qs.list')}</h2>
				{#if !sets}
					<p class="muted">{t('common.loading')}</p>
				{:else if sets.length}
					<ul class="sets">
						{#each sets as s (s.id)}
							<li>
								<a class="serif name" href="/research/questions/{s.id}">{s.name}</a>
								<p class="small muted">
									{t('qs.count', { n: s.questions ?? 0 })} · {t('qs.onVersion', { n: s.corpus_version })} ·
									{s.imported ? t('qs.importedFrom', { who: s.created_by }) : t('research.createdBy', { who: s.created_by, date: formatDay(s.created_at) })}
								</p>
								{#if s.frozen}<span class="chip dark"><Icon name="lock" size={14} />{t('qs.frozenChip')}</span>{/if}
							</li>
						{/each}
					</ul>
				{:else}
					<p class="muted">{t('qs.empty')}</p>
				{/if}
			</section>

			<div class="stack">
				<form class="panel" onsubmit={create}>
					<h2 class="heading"><StepTag n={1} />{t('qs.create')}</h2>
					{#if versions.length}
						<label class="field"><span>{t('qs.name')}</span><input maxlength="120" required bind:value={name} placeholder={t('qs.namePh')} /></label>
						<label class="field"><span>{t('qs.version')}</span>
							<select bind:value={versionId}>
								{#each versions as v (v.id)}<option value={v.id}>{v.corpus_name} · {t('corpus.version', { n: v.number })} ({t('research.docs', { n: v.document_count })})</option>{/each}
							</select>
							<span class="hint">{t('qs.versionHint')}</span>
						</label>
						<label class="field"><span>{t('qs.guideline')} <span class="hint">({t('common.optional')})</span></span><textarea rows="4" maxlength="20000" bind:value={guideline} placeholder={t('qs.guidelinePh')}></textarea></label>
						<div><button class="btn primary" type="submit" disabled={busy}><Icon name="plus" />{t('qs.createSubmit')}</button></div>
					{:else}
						<p class="small">{t('qs.noVersion')} <a href="/research">{t('research.title')}</a></p>
					{/if}
				</form>

				<section class="panel">
					<h2 class="heading"><StepTag n={1} />{t('qs.importPack')}</h2>
					<p class="small muted">{t('qs.importPackLead')}</p>
					<label class="field"><span>{t('qs.packFile')}</span><input type="file" accept=".json,application/json" disabled={busy} onchange={importPack} /></label>
				</section>
			</div>
		</div>
	{/if}
</div>

<style>
	.status {
		display: flex;
		align-items: center;
		gap: 8px;
		margin: 0 0 20px;
		color: var(--ink-2);
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
	.name {
		font-size: 1.15rem;
		font-weight: 600;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 4px;
	}
	@media (max-width: 900px) {
		.cols {
			grid-template-columns: 1fr;
		}
	}
</style>
