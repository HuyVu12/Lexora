<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDate } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import type { AuditSetSummary } from '#lib/types.js';

	let data = $state<{ sets: AuditSetSummary[]; can_score: boolean } | null>(null);
	let error = $state('');
	$effect(() => {
		if (canReview(session.account))
			api<{ sets: AuditSetSummary[]; can_score: boolean }>('/api/audit')
				.then((v) => (data = v))
				.catch((e) => (error = e.message));
	});
	const mine = (s: AuditSetSummary) => s.labelled[session.account?.username ?? '']?.n ?? 0;
</script>

<svelte:head><title>{t('audit.title')} · Lexora</title></svelte:head>

<div class="page">
	{#if !canReview(session.account)}
		<h1 class="title">{t('common.forbidden.title')}</h1>
		<p class="lead">{t('common.forbidden.body')}</p>
	{:else}
		<header class="page-head">
			<div>
				<h1 class="title">{t('audit.title')}</h1>
				<p class="lead">{t('audit.lead')}</p>
			</div>
			<a class="btn quiet" href="/docs/huong-dan-kiem-tra-quy-pham"><Icon name="doc" size={16} />{t('audit.guide')}</a>
		</header>
		{#if error}
			<p class="notice error" role="alert">{error}</p>
		{:else if !data}
			<p class="muted">{t('common.loading')}</p>
		{:else if !data.sets.length}
			<p class="muted">{t('audit.empty')}</p>
		{:else}
			<ul class="sets">
				{#each data.sets as s (s.id)}
					<li class="panel">
						<div class="head">
							<a class="name" href="/research/audit/{s.id}">{s.name}</a>
							<span class="small muted">{formatDate(s.created_at)}</span>
						</div>
						<progress max={s.items} value={mine(s)} aria-label={t('audit.mine', { done: mine(s), n: s.items })}></progress>
						<p class="small">{t('audit.mine', { done: mine(s), n: s.items })}</p>
						<p class="small muted">
							{Object.entries(s.labelled).map(([who, v]) => `${v.name} (@${who}): ${v.n}`).join(' · ') || t('audit.noneYet')}
							· {t('audit.adjudicatedN', { n: s.adjudicated, total: s.items })}
						</p>
						<div class="row">
							<a class="btn primary small" href="/research/audit/{s.id}">{t('audit.open')}<Icon name="arrow" size={16} /></a>
							{#if data.can_score}<a class="btn small" href="/research/audit/{s.id}/score">{t('audit.score')}</a>{/if}
						</div>
					</li>
				{/each}
			</ul>
		{/if}
	{/if}
</div>

<style>
	.sets {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
		gap: 14px;
	}
	.sets .panel {
		display: grid;
		gap: 8px;
	}
	.head {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: 10px;
	}
	.name {
		font-weight: 600;
		font-size: 16px;
		color: var(--ink);
	}
	progress {
		width: 100%;
	}
	.row {
		gap: 8px;
		margin-top: 4px;
	}
</style>
