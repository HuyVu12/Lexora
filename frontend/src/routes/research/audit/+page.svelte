<script module lang="ts">
	import type { AuditSetSummary } from '#lib/types.js';
	type Listing = { sets: AuditSetSummary[]; can_score: boolean };
	// The last listing shows at once when you come back; a fresh one replaces it when it arrives.
	let last: Listing | null = null;
</script>

<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import Skeleton from '#lib/components/Skeleton.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDate } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { revealItems } from '#lib/motion.js';

	let data = $state<Listing | null>(last);
	const fresh = !last;
	let error = $state('');
	$effect(() => {
		if (canReview(session.account))
			api<Listing>('/api/audit')
				.then((v) => (data = last = v))
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
				<p class="facts">
					{#if data}
						<span><strong>{data.sets.length}</strong> {t('audit.facts.sets', { n: data.sets.length })}</span>
					{:else}
						{#each [110] as w (w)}<span><Skeleton width="{w}px" height="12px" /></span>{/each}
					{/if}
				</p>
			</div>
			<a class="btn quiet" href="/docs/huong-dan-kiem-tra-quy-pham"><Icon name="doc" size={16} />{t('audit.guide')}</a>
		</header>
		{#if error}
			<p class="notice error" role="alert">{error}</p>
		{:else if !data}
			<div aria-busy="true">
				<span class="visually-hidden" role="status">{t('common.loading')}</span>
				<ul class="cards" aria-hidden="true">
					{#each [0, 1] as i (i)}
						<li class="panel card-row">
							<span class="body"><Skeleton width="40%" height="17px" /><Skeleton width="62%" height="11px" /></span>
							<span class="side"><Skeleton width="150px" height="11px" /><Skeleton width="150px" height="6px" radius="3px" /></span>
						</li>
					{/each}
				</ul>
			</div>
		{:else if !data.sets.length}
			<p class="empty-note">{t('audit.empty')}</p>
		{:else}
			<ul class="cards" {@attach fresh && revealItems({ step: 40 })}>
				{#each data.sets as s (s.id)}
					<li class="panel panel-link card-row stretch">
						<span class="body">
							<a class="name stretch-link" href="/research/audit/{s.id}">{s.name}</a>
							<span class="dotted">
								<span>{formatDate(s.created_at)}</span>
								{#each Object.entries(s.labelled).filter(([who]) => who !== session.account?.username) as [who, v] (who)}<span>{v.name}: {v.n}</span>{/each}
								<span>{t('audit.adjudicatedN', { n: s.adjudicated, total: s.items })}</span>
							</span>
						</span>
						<span class="side">
							<span class="small">{t('audit.mine', { done: mine(s), n: s.items })}</span>
							<span class="meter" aria-hidden="true"><i style:transform="scaleX({s.items ? Math.min(mine(s), s.items) / s.items : 0})"></i></span>
							{#if data.can_score}<a class="btn small above" href="/research/audit/{s.id}/score">{t('audit.score')}</a>{/if}
						</span>
					</li>
				{/each}
			</ul>
		{/if}
	{/if}
</div>

<style>
	.side .meter {
		width: 160px;
	}
	.side .btn {
		margin-top: 4px;
	}
	@media (max-width: 640px) {
		.side,
		.side .meter {
			width: 100%;
		}
	}
</style>
