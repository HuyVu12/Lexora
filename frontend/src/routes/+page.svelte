<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import Term from '#lib/components/Term.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDate } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import type { AppState } from '#lib/types.js';

	let app = $state<AppState | null>(null);
	let error = $state('');
	$effect(() => {
		api<AppState>('/api/state').then((s) => (app = s)).catch((e) => (error = e.message));
	});
	const reviewer = $derived(canReview(session.account));
	const drafts = $derived((app?.drafts ?? []).filter((d) => d.status === 'draft'));
</script>

<svelte:head><title>{t('nav.home')} · Lexora</title></svelte:head>

<div class="page">
	<header class="page-head">
		<div>
			<h1 class="title">{t('home.hello', { name: session.account?.display_name ?? '' })}</h1>
			<p class="lead">{reviewer ? t('home.lead.reviewer') : t('home.lead.reader')}</p>
		</div>
		<div class="row">
			<a class="btn" href="/chat"><Icon name="chat" />{t('home.ask')}</a>
			{#if reviewer}<a class="btn primary" href="/import"><Icon name="upload" />{t('home.import')}</a>{/if}
		</div>
	</header>

	{#if error}<p class="notice error" role="alert">{error}</p>{/if}

	{#if !app && !error}
		<p class="muted">{t('common.loading')}</p>
	{:else if app}
		<div class="layout">
			<div class="stack">
				{#if reviewer}
					<section aria-labelledby="drafts-h">
						<h2 id="drafts-h" class="subtitle">{t('home.drafts.title')}</h2>
						{#if drafts.length}
							<ul class="list">
								{#each drafts as d (d.id)}
									<li>
										<a class="item sheet" href="/drafts/{d.id}">
											<span class="doc"><Icon name="doc" /></span>
											<span class="body">
												<strong>{d.title}</strong>
												<span class="small muted">{d.target.mode === 'new' ? t('review.target.new', { name: d.target.name ?? '' }) : t('review.target.merge', { name: d.kb_name })}</span>
											</span>
											<span class="state small">
												{#if ['queued', 'running'].includes(d.extraction_state)}{t('home.drafts.extracting')}{:else}
													<span class="meter" aria-hidden="true"><i style:width="{d.claims ? (100 * Math.min(d.decided, d.claims)) / d.claims : 0}%"></i></span>
													{t('home.drafts.decided', { done: Math.min(d.decided, d.claims), total: d.claims })}
												{/if}
											</span>
										</a>
									</li>
								{/each}
							</ul>
						{:else}
							<p class="empty">{t('home.drafts.empty')}</p>
						{/if}
					</section>
				{/if}

				<section aria-labelledby="kbs-h">
					<h2 id="kbs-h" class="subtitle">{t('home.kbs.title')}</h2>
					{#if app.knowledge_bases.length}
						<ul class="kbs">
							{#each app.knowledge_bases as kb (kb.id)}
								<li>
									<a class="kb sheet" href="/kb/{kb.id}">
										<span class="kb-body">
											<span class="kb-top"><strong class="serif">{kb.name}</strong><span class="chip {kb.data_class}">{kb.data_class === 'private' ? t('kb.private') : t('kb.public')}</span></span>
											{#if kb.description}<span class="small muted">{kb.description}</span>{/if}
											<span class="facts small">
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
						<p class="empty">{reviewer ? t('home.kbs.empty.reviewer') : t('home.kbs.empty.reader')}</p>
					{/if}
				</section>
			</div>

			<aside class="stack">
				<section class="panel">
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
				<section class="panel intro">
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
	.layout {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 340px;
		gap: 32px;
		align-items: start;
	}
	.stack > section {
		display: grid;
		gap: 12px;
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
		color: var(--ink);
		text-decoration: none;
		transition: transform 0.18s var(--ease-out), box-shadow 0.18s var(--ease-out);
	}
	.item:hover,
	.kb:hover {
		transform: translateY(-2px);
		box-shadow: var(--shadow-pop);
		text-decoration: none;
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
		gap: 2px;
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
	}
	.kbs {
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 14px;
	}
	.kb {
		display: grid;
		color: var(--ink);
		text-decoration: none;
		overflow: hidden;
		transition: transform 0.18s var(--ease-out), box-shadow 0.18s var(--ease-out);
	}
	.kb-body {
		display: grid;
		gap: 8px;
		align-content: start;
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
	.facts {
		display: flex;
		gap: 4px 16px;
		flex-wrap: wrap;
		margin-top: auto;
		color: var(--ink-2);
	}
	.empty {
		padding: 20px;
		border: 1px dashed var(--rule-strong);
		border-radius: var(--r-panel);
		color: var(--muted);
	}
	.chats li {
		display: grid;
		gap: 2px;
	}
	.intro {
		display: grid;
		gap: 10px;
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
</style>
