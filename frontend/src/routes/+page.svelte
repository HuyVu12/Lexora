<script lang="ts">
	import PageGuide from '#lib/components/PageGuide.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import Term from '#lib/components/Term.svelte';
	import Skeleton from '#lib/components/Skeleton.svelte';
	import { cachedAppState, loadAppState } from '#lib/app-state.svelte.js';
	import { t, formatDate } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { countUp, revealItems } from '#lib/motion.js';

	// The last copy of the state shows at once (coming back from another page is instant); a fresh copy
	// replaces it when it arrives. The first visit shows skeletons shaped like the real lists.
	let error = $state('');
	const app = $derived(cachedAppState());
	// Lists cascade in only when they replace skeletons; coming back to a cached overview is instant.
	const fresh = !cachedAppState();
	$effect(() => {
		loadAppState().catch((e) => (error = e.message));
	});
	const reviewer = $derived(canReview(session.account));
	const drafts = $derived((app?.drafts ?? []).filter((d) => d.status === 'draft'));
	const norms = $derived((app?.knowledge_bases ?? []).reduce((sum, kb) => sum + kb.approved_claims, 0));
	const stats = $derived(
		app
			? [
					{ n: app.knowledge_bases.length, key: 'home.stat.kbs' as const },
					{ n: norms, key: 'home.stat.norms' as const },
					reviewer ? { n: drafts.length, key: 'home.stat.drafts' as const } : { n: app.chat_sessions.length, key: 'home.stat.chats' as const }
				]
			: []
	);
</script>

<svelte:head><title>{t('nav.home')} · Lexora</title></svelte:head>

<div class="page">
	<header class="page-head">
		<div>
			<h1 class="title">{t('home.hello', { name: session.account?.display_name ?? '' })}</h1>
			<ul class="stats" aria-label={t('home.stat.label')}>
				{#if app}
					{#each stats as s (s.key)}
						<li><strong {@attach countUp(s.n, { duration: fresh ? 700 : 0 })}></strong> {t(s.key, { n: s.n })}</li>
					{/each}
				{:else}
					{#each [110, 170, 150] as w (w)}<li><Skeleton width="{w}px" height="12px" /></li>{/each}
				{/if}
			</ul>
		</div>
		<div class="row">
			<a class="btn" href="/chat"><Icon name="chat" />{t('home.ask')}</a>
			{#if reviewer}<a class="btn primary" href="/import"><Icon name="upload" />{t('home.import')}</a>{/if}
		</div>
	</header>
	{#if reviewer}<PageGuide name="homeReviewer" steps={3} />{:else}<PageGuide name="homeReader" steps={3} />{/if}

	{#if error}<p class="notice error" role="alert">{error}</p>{/if}

	{#if !app && !error}
		<div class="layout" aria-busy="true">
			<span class="visually-hidden" role="status">{t('common.loading')}</span>
			<div class="stack">
				{#if reviewer}
					<section class="block">
						<h2 class="subtitle">{t('home.drafts.title')}</h2>
						<div class="list">
							{#each [0, 1] as i (i)}
								<div class="item panel">
									<Skeleton width="40px" height="40px" radius="8px" />
									<span class="body"><Skeleton width="58%" height="15px" /><Skeleton width="38%" height="11px" /></span>
									<span class="state"><Skeleton width="140px" height="6px" radius="3px" /><Skeleton width="150px" height="11px" /></span>
								</div>
							{/each}
						</div>
					</section>
				{/if}
				<section class="block">
					<h2 class="subtitle">{t('home.kbs.title')}</h2>
					<div class="kbs">
						{#each [0, 1, 2] as i (i)}
							<div class="kb panel">
								<span class="kb-body">
									<span class="kb-top"><Skeleton width="62%" height="18px" /><Skeleton width="64px" height="20px" radius="999px" /></span>
									<Skeleton lines={2} height="11px" gap="8px" last="70%" />
									<span class="kb-facts"><Skeleton width="72px" height="11px" /><Skeleton width="120px" height="11px" /></span>
								</span>
							</div>
						{/each}
					</div>
				</section>
			</div>
			<aside class="stack">
				<section class="panel side">
					<h2 class="heading">{t('home.chats.title')}</h2>
					<div class="chats">
						{#each [0, 1, 2] as i (i)}<div class="chat-ghost"><Skeleton width="78%" height="13px" /><Skeleton width="46%" height="11px" /></div>{/each}
					</div>
				</section>
			</aside>
		</div>
	{:else if app}
		<div class="layout">
			<div class="stack">
				{#if reviewer}
					<section class="block" aria-labelledby="drafts-h">
						<h2 id="drafts-h" class="subtitle">{t('home.drafts.title')}</h2>
						{#if drafts.length}
							<ul class="list" {@attach fresh && revealItems()}>
								{#each drafts as d (d.id)}
									<li>
										<a class="item panel panel-link" href="/drafts/{d.id}">
											<span class="doc"><Icon name="doc" /></span>
											<span class="body">
												<strong>{d.title}</strong>
												<span class="small muted">{d.target.mode === 'new' ? t('review.target.new', { name: d.target.name ?? '' }) : t('review.target.merge', { name: d.kb_name })}</span>
											</span>
											<span class="state small">
												{#if ['queued', 'running'].includes(d.extraction_state)}{t('home.drafts.extracting')}{:else}
													<span class="meter" aria-hidden="true"><i style:transform="scaleX({d.claims ? Math.min(d.decided, d.claims) / d.claims : 0})"></i></span>
													{t('home.drafts.decided', { done: Math.min(d.decided, d.claims), total: d.claims })}
												{/if}
											</span>
										</a>
									</li>
								{/each}
							</ul>
						{:else}
							<p class="empty-note">{t('home.drafts.empty')}</p>
						{/if}
					</section>
				{/if}

				<section class="block" aria-labelledby="kbs-h">
					<h2 id="kbs-h" class="subtitle">{t('home.kbs.title')}</h2>
					{#if app.knowledge_bases.length}
						<ul class="kbs" {@attach fresh && revealItems({ delay: 60 })}>
							{#each app.knowledge_bases as kb (kb.id)}
								<li>
									<a class="kb panel panel-link" href="/kb/{kb.id}">
										<span class="kb-body">
											<span class="kb-top"><strong class="serif">{kb.name}</strong><span class="chip {kb.data_class}">{kb.data_class === 'private' ? t('kb.private') : t('kb.public')}</span></span>
											{#if kb.description}<span class="small muted">{kb.description}</span>{/if}
											<span class="kb-facts small">
												<span>{t('home.kb.docs', { n: kb.documents })}</span>
												<span>{t('home.kb.norms', { n: kb.approved_claims })}</span>
												<span class="muted">{t('home.kb.updated', { date: formatDate(kb.updated_at) })}</span>
											</span>
										</span>
									</a>
								</li>
							{/each}
						</ul>
					{:else}
						<p class="empty-note">{reviewer ? t('home.kbs.empty.reviewer') : t('home.kbs.empty.reader')}</p>
					{/if}
				</section>
			</div>

			<aside class="stack">
				<section class="panel side">
					<h2 class="heading">{t('home.chats.title')}</h2>
					{#if app.chat_sessions.length}
						<ul class="chats">
							{#each app.chat_sessions.slice(0, 6) as s (s.id)}
								<li>
									<a href="/chat/{s.id}">{s.bindings.map((b) => b.kb_name ?? t('chat.deletedKb')).join(', ')}</a>
									<span class="small muted">{formatDate(s.created_at)} · {t('home.chats.turns', { n: s.turns })}</span>
								</li>
							{/each}
						</ul>
					{:else}
						<p class="small muted">{t('home.chats.empty')}</p>
					{/if}
				</section>
				<section class="panel side intro">
					<h2 class="heading">{t('home.intro.title')}</h2>
					<p class="small">{t('home.intro.body')}</p>
					<p class="specimen serif" aria-hidden="true">
						<mark class="hl-actor">người sử dụng lao động</mark> <b>phải</b> <mark class="hl-action">thông báo</mark> <mark class="hl-object">kết quả thử việc</mark>
					</p>
					<p class="small"><Term key="norm" /> · <Term key="evidence" /> · <Term key="approved" /></p>
					<a href="/about">{t('home.intro.more')}</a>
				</section>
			</aside>
		</div>
	{/if}
</div>

<style>
	.stats {
		display: flex;
		flex-wrap: wrap;
		gap: 4px 0;
		margin: 8px 0 0;
		padding: 0;
		list-style: none;
		min-height: 23px;
		align-items: center;
		color: var(--ink-2);
	}
	.stats li {
		display: inline-flex;
		align-items: baseline;
		gap: 5px;
	}
	.stats li + li::before {
		content: '';
		width: 3px;
		height: 3px;
		margin: 0 12px;
		border-radius: 50%;
		background: var(--rule-strong);
		align-self: center;
	}
	.stats strong {
		font-weight: 600;
		color: var(--ink);
	}
	.layout {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 340px;
		gap: var(--space-8);
		align-items: start;
	}
	.block {
		display: grid;
		gap: var(--space-3);
	}
	.stack {
		gap: var(--space-8);
	}
	aside.stack {
		gap: var(--space-4);
	}
	.list,
	.kbs,
	.chats {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 10px;
	}
	.item {
		display: grid;
		grid-template-columns: 40px minmax(0, 1fr) auto;
		gap: 14px;
		align-items: center;
		padding: 14px 18px;
	}
	.doc {
		width: 40px;
		height: 40px;
		border-radius: 8px;
		display: grid;
		place-items: center;
		background: var(--desk);
		color: var(--ink-2);
	}
	.body {
		display: grid;
		gap: 4px;
		min-width: 0;
	}
	.state {
		display: grid;
		justify-items: end;
		gap: 6px;
		color: var(--ink-2);
	}
	.meter {
		width: 140px;
		height: 6px;
		border-radius: 3px;
		background: var(--desk-2);
		overflow: hidden;
	}
	.meter i {
		display: block;
		height: 100%;
		background: var(--approve);
		transform-origin: 0 50%;
		transition: transform var(--dur-slow) var(--ease-out);
	}
	.kbs {
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 14px;
	}
	.kb {
		display: grid;
		padding: 0;
		overflow: hidden;
		height: 100%;
	}
	.kbs > li {
		display: grid;
	}
	.kb-body {
		display: grid;
		gap: 8px;
		align-content: start;
		grid-template-rows: auto auto 1fr;
		padding: 18px 20px;
	}
	.kb-top {
		display: flex;
		justify-content: space-between;
		gap: 10px;
		align-items: flex-start;
	}
	.kb-top strong {
		font-size: 18px;
		line-height: 1.3;
		font-weight: 600;
	}
	.kb-facts {
		display: flex;
		gap: 4px 16px;
		flex-wrap: wrap;
		align-self: end;
		margin-top: 4px;
		color: var(--ink-2);
	}
	.chat-ghost {
		display: grid;
		gap: 7px;
		padding: 3px 0;
	}
	.side {
		display: grid;
		gap: 10px;
		padding: 20px 22px;
	}
	.chats li {
		display: grid;
		gap: 2px;
	}
	.chats a {
		text-decoration-color: color-mix(in srgb, currentColor 35%, transparent);
	}
	.specimen {
		font-size: 15px;
		line-height: 1.9;
	}
	.specimen mark {
		background: var(--hl);
		color: var(--ink);
		padding: 1px 2px;
		border-radius: 2px;
	}
	.specimen b {
		font-weight: 600;
		border-radius: 999px;
		box-shadow: 0 0 0 1.5px var(--ink-2);
		padding: 0 3px;
	}
	@media (max-width: 960px) {
		.layout {
			grid-template-columns: 1fr;
		}
	}
	@media (max-width: 640px) {
		.stats {
			gap: 2px 14px;
		}
		.stats li + li::before {
			display: none;
		}
		.item {
			grid-template-columns: 40px minmax(0, 1fr);
		}
		.state {
			grid-column: 1 / -1;
			justify-items: start;
		}
	}
</style>
