<script lang="ts">
	import PageGuide from '#lib/components/PageGuide.svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import Steps from '#lib/components/Steps.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import { api, ApiError } from '#lib/api.js';
	import { t } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { notify } from '#lib/toast.svelte.js';
	import type { Draft } from '#lib/types.js';

	let draft = $state<Draft | null>(null);
	let error = $state('');
	let reason = $state('');
	let confirmed = $state(false);
	let busy = $state(false);
	let conflict = $state('');
	const id = $derived(page.params.id ?? '');

	$effect(() => {
		if (canReview(session.account)) api<Draft>(`/api/draft?id=${encodeURIComponent(id)}`).then((d) => (draft = d)).catch((e) => (error = e.message));
	});

	const p = $derived(draft?.progress);
	const blocked = $derived(!p || p.undecided > 0 || p.gaps_open > 0 || p.approved === 0);
	const target = $derived(
		draft ? (draft.target.mode === 'new' ? t('preview.targetNew', { name: draft.target.name ?? '' }) : t('preview.targetKb', { name: draft.kb?.name ?? '' })) : ''
	);

	async function publish(event: SubmitEvent) {
		event.preventDefault();
		if (!confirmed) return notify({ key: 'preview.mustCheck' }, true);
		busy = true;
		try {
			const result = await api<{ kb_id: string }>('/api/publish', { draft_id: id, reason });
			await goto(`/kb/${result.kb_id}?published=1`);
		} catch (e) {
			if (e instanceof ApiError && e.code === 'base_changed') conflict = e.message;
			else notify(e instanceof Error ? e.message : String(e), true);
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>{t('preview.title')} · Lexora</title></svelte:head>

<div class="page narrow">
	{#if !canReview(session.account)}
		<h1 class="title">{t('common.forbidden.title')}</h1>
	{:else if error}
		<p class="notice error" role="alert">{error}</p>
	{:else if !draft || !p}
		<p class="muted">{t('common.loading')}</p>
	{:else}
		<Steps current={3} />
		<header class="page-head">
			<div>
				<h1 class="title">{t('preview.title')}</h1>
				<p class="lead serif">{draft.title}</p>
			</div>
		</header>
		<PageGuide name="preview" steps={3} />

		<section class="sheet summary">
			<p class="headline serif">{t('preview.summary', { n: draft.diff.approved, target })}</p>
			<table class="table">
				<thead><tr><th scope="col"></th><th scope="col" class="num">{t('preview.col.now')}</th><th scope="col" class="num">{t('preview.col.after')}</th><th scope="col" class="num">{t('preview.col.change')}</th></tr></thead>
				<tbody>
					{#each [[t('preview.row.docs'), draft.diff.documents_before, draft.diff.documents_after], [t('preview.row.norms'), draft.diff.claims_before, draft.diff.claims_after]] as [label, before, after] (label)}
						<tr><td>{label}</td><td class="num">{before}</td><td class="num">{after}</td><td class="num delta">{Number(after) > Number(before) ? `+${Number(after) - Number(before)}` : ''}</td></tr>
					{/each}
				</tbody>
			</table>
			<dl class="facts">
				<div><dt>{t('preview.rejected')}</dt><dd>{draft.diff.rejected}</dd></div>
				<div><dt>{t('preview.edited')}</dt><dd>{draft.diff.edited}</dd></div>
				{#if p.gaps}<div><dt>{t('preview.noNorm')}</dt><dd>{p.gaps - p.gaps_open}</dd></div>{/if}
				{#if draft.target.mode === 'merge'}<div><dt>{t('preview.linked')}</dt><dd>{draft.diff.entities_linked}</dd></div>{/if}
				<div><dt>{t('preview.newEntities')}</dt><dd>{draft.diff.entities_new}</dd></div>
			</dl>
			{#each draft.diff.warnings as w (w)}<p class="notice warn">{w}</p>{/each}
			{#if p.undecided}<p class="notice error">{t('preview.block.undecided', { n: p.undecided })}</p>{/if}
			{#if p.gaps_open}<p class="notice error">{t('preview.block.gaps', { n: p.gaps_open })}</p>{/if}
			{#if p.total && !p.approved && !p.undecided}<p class="notice error">{t('preview.block.none')}</p>{/if}
			<p class="notice info">{t('preview.validity')}</p>
		</section>

		<form class="panel confirm" onsubmit={publish}>
			<h2 class="heading">{t('preview.confirm.title')}</h2>
			<p><span class="label">{t('preview.reviewer')}</span><br /><strong>{session.account?.display_name}</strong> <span class="muted">@{session.account?.username}</span></p>
			<label class="field"><span>{t('preview.reason')}</span><textarea rows="3" maxlength="2000" required placeholder={t('preview.reasonPh')} bind:value={reason}></textarea></label>
			<label class="check"><input type="checkbox" bind:checked={confirmed} />{t('preview.check')}</label>
			{#if conflict}
				<div class="notice error" role="alert"><p>{conflict}</p><a class="btn small" href="/import?kb={draft.target.kb_id}">{t('preview.reimport')}</a></div>
			{/if}
			<div class="row">
				<a class="btn" href="/drafts/{id}"><Icon name="back" />{t('preview.back')}</a>
				<button class="btn primary" type="submit" disabled={blocked || busy}>{t('preview.publish')}</button>
			</div>
		</form>
	{/if}
</div>

<style>
	.narrow {
		max-width: 860px;
	}
	.summary {
		padding: 28px 32px;
		display: grid;
		gap: 16px;
		margin-bottom: 20px;
	}
	.headline {
		font-size: 21px;
		line-height: 1.5;
	}
	.delta {
		color: var(--approve);
		font-weight: 600;
	}
	.facts {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
		gap: 8px 24px;
		margin: 0;
	}
	.facts div {
		display: flex;
		justify-content: space-between;
		gap: 12px;
		padding: 8px 0;
		border-bottom: 1px solid var(--rule);
	}
	.facts dd {
		margin: 0;
		font-weight: 600;
	}
	.confirm {
		display: grid;
		gap: 14px;
	}
	.confirm .notice {
		display: grid;
		gap: 8px;
		justify-items: start;
	}
</style>
