<script module lang="ts">
	import type { FrozenVersionOption, QuestionSetSummary } from '#lib/types.js';
	type Listing = { sets: QuestionSetSummary[]; versions: FrozenVersionOption[]; proposal_model: string | null };
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
	let guideline = $state('');
	let busy = $state(false);

	const sets = $derived(data?.sets ?? null);
	const versions = $derived(data?.versions ?? []);
	const model = $derived(data?.proposal_model ?? null);
	const frozenCount = $derived(sets?.filter((s) => s.frozen).length ?? 0);

	const load = () =>
		api<Listing>('/api/question-sets')
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
				<p class="facts">
					{#if sets}
						<span><strong>{sets.length}</strong> {t('qs.facts.sets', { n: sets.length })}</span>
						<span><strong>{frozenCount}</strong> {t('qs.facts.frozen', { n: frozenCount })}</span>
						<span title={model ? t('qs.model.on', { model }) : t('qs.model.off')}>{model ? t('qs.facts.modelOn', { model }) : t('qs.facts.modelOff')}</span>
					{:else}
						{#each [110, 90, 190] as w (w)}<span><Skeleton width="{w}px" height="12px" /></span>{/each}
					{/if}
				</p>
			</div>
		</header>
		<PageGuide name="qsets" steps={2} />

		<div class="cols">
			<section class="section" aria-labelledby="sets-heading" aria-busy={!sets}>
				<h2 class="subtitle" id="sets-heading"><StepTag n={2} />{t('qs.list')}</h2>
				{#if !sets}
					<span class="visually-hidden" role="status">{t('common.loading')}</span>
					<ul class="cards" aria-hidden="true">
						{#each [0, 1, 2] as i (i)}
							<li class="panel card-row"><span class="body"><Skeleton width="48%" height="17px" /><Skeleton width="64%" height="11px" /></span><span class="side"><Skeleton width="70px" height="20px" radius="999px" /></span></li>
						{/each}
					</ul>
				{:else if sets.length}
					<ul class="cards" {@attach fresh && revealItems({ step: 40 })}>
						{#each sets as s (s.id)}
							<li>
								<a class="panel panel-link card-row" href="/research/questions/{s.id}">
									<span class="body">
										<span class="name">{s.name}</span>
										<span class="dotted">
											<span>{t('qs.onVersion', { n: s.corpus_version })}</span>
											<span>{s.imported ? t('qs.importedFrom', { who: s.created_by }) : t('research.createdBy', { who: s.created_by, date: formatDay(s.created_at) })}</span>
										</span>
									</span>
									<span class="side">
										<span class="small">{t('qs.count', { n: s.questions ?? 0 })}</span>
										{#if s.frozen}<span class="chip dark"><Icon name="lock" size={13} />{t('qs.frozenChip')}</span>{/if}
									</span>
								</a>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="empty-note">{t('qs.empty')}</p>
				{/if}
			</section>

			<div class="side-stack">
				<form class="panel form" onsubmit={create}>
					<h2 class="heading"><StepTag n={1} />{t('qs.create')}</h2>
					{#if !data}
						<Skeleton lines={3} height="38px" gap="14px" last="100%" />
					{:else if versions.length}
						<label class="field"><span>{t('qs.name')}</span><input maxlength="120" required bind:value={name} placeholder={t('qs.namePh')} /></label>
						<label class="field"><span>{t('qs.version')}</span>
							<select bind:value={versionId}>
								{#each versions as v (v.id)}<option value={v.id}>{v.corpus_name} · {t('corpus.version', { n: v.number })} ({t('research.docs', { n: v.document_count })})</option>{/each}
							</select>
							<span class="hint">{t('qs.versionHint')}</span>
						</label>
						<label class="field"><span>{t('qs.guideline')} <span class="hint">({t('common.optional')})</span></span><textarea rows="3" maxlength="20000" bind:value={guideline} placeholder={t('qs.guidelinePh')}></textarea></label>
						<div><button class="btn primary" type="submit" disabled={busy}><Icon name="plus" />{t('qs.createSubmit')}</button></div>
					{:else}
						<p class="small">{t('qs.noVersion')} <a href="/research">{t('research.title')}</a></p>
					{/if}
				</form>

				<section class="panel form">
					<h2 class="heading"><StepTag n={1} />{t('qs.importPack')}</h2>
					<p class="small muted">{t('qs.importPackLead')}</p>
					<label class="field"><span>{t('qs.packFile')}</span><input type="file" accept=".json,application/json" disabled={busy} onchange={importPack} /></label>
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
	.form .field textarea {
		min-height: 88px;
	}
	.chip :global(svg) {
		flex: none;
	}
	@media (max-width: 960px) {
		.cols {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
