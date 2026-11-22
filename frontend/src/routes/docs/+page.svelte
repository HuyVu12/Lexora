<script module lang="ts">
	import type { DocEntry } from '#lib/types.js';
	// The list shows at once when you come back from reading a document.
	let last: DocEntry[] | null = null;
</script>

<script lang="ts">
	import Skeleton from '#lib/components/Skeleton.svelte';
	import { revealItems } from '#lib/motion.js';
	import Icon from '#lib/components/Icon.svelte';
	import { api } from '#lib/api.js';
	import { t } from '#lib/i18n/index.svelte.js';
	import { session } from '#lib/session.svelte.js';

	let documents = $state<DocEntry[] | null>(last);
	const fresh = !last;
	let error = $state('');
	let query = $state('');

	$effect(() => {
		if (session.account)
			api<{ documents: DocEntry[] }>('/api/docs')
				.then((v) => (documents = last = v.documents))
				.catch((e) => (error = e.message));
	});

	const fold = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/gi, 'd').toLowerCase();
	const shown = $derived((documents ?? []).filter((d) => !query.trim() || fold(`${d.title} ${d.summary} ${d.category}`).includes(fold(query.trim()))));
	const groups = $derived(
		[...new Set(shown.map((d) => d.category))].map((category) => ({ category, items: shown.filter((d) => d.category === category) }))
	);
	const date = (value: string | null) => (value ? value.split('-').reverse().join('/') : '');
</script>

<svelte:head><title>{t('docs.title')} · Lexora</title></svelte:head>

<div class="page">
	<header class="page-head">
		<div>
			<h1 class="title">{t('docs.title')}</h1>
			<p class="facts">
				{#if documents}
					<span><strong>{documents.length}</strong> {t('docs.facts.n', { n: documents.length })}</span>
				{:else}
					<span><Skeleton width="90px" height="12px" /></span>
				{/if}
			</p>
		</div>
		<label class="search">
			<span class="visually-hidden">{t('docs.search')}</span>
			<Icon name="search" size={16} />
			<input class="input" type="search" placeholder={t('docs.search')} bind:value={query} />
		</label>
	</header>

	{#if error}
		<p class="notice error" role="alert">{error}</p>
	{:else if !documents}
		<div aria-busy="true">
			<span class="visually-hidden" role="status">{t('common.loading')}</span>
			{#each [3, 2] as n, g (g)}
				<section class="group" aria-hidden="true">
					<Skeleton width="120px" height="12px" />
					<ul class="index panel">
						{#each { length: n } as _, i (i)}
							<li><span class="row-link ghost"><Skeleton width="36px" height="36px" radius="6px" /><span class="text"><Skeleton width="44%" height="15px" /><Skeleton width="78%" height="12px" /></span></span></li>
						{/each}
					</ul>
				</section>
			{/each}
		</div>
	{:else if !documents.length}
		<p class="empty-note">{t('docs.empty')}</p>
	{:else if !shown.length}
		<p class="empty-note">{t('docs.noMatch')}</p>
	{:else}
		<div {@attach fresh && revealItems({ step: 50, cap: 4 })}>
			{#each groups as group (group.category)}
				<section class="group" aria-labelledby="cat-{group.category}">
					<h2 class="label" id="cat-{group.category}">{group.category} <span class="count">{group.items.length}</span></h2>
					<ul class="index panel">
						{#each group.items as doc (doc.slug)}
							<li>
								<a class="row-link" href="/docs/{doc.slug}">
									<span class="icon" aria-hidden="true"><Icon name="doc" size={18} /></span>
									<span class="text">
										<strong>{doc.title}</strong>
										{#if doc.summary}<span class="summary">{doc.summary}</span>{/if}
									</span>
									{#if doc.updated}<span class="small muted when">{t('docs.updated', { date: date(doc.updated) })}</span>{/if}
									<span class="go" aria-hidden="true"><Icon name="arrow" size={16} /></span>
								</a>
							</li>
						{/each}
					</ul>
				</section>
			{/each}
		</div>
	{/if}
</div>

<style>
	.search {
		position: relative;
		display: flex;
		align-items: center;
		width: min(320px, 100%);
	}
	.search :global(svg) {
		position: absolute;
		left: 11px;
		color: var(--muted);
		pointer-events: none;
	}
	.search .input {
		padding-left: 34px;
	}
	.group {
		display: grid;
		gap: 10px;
		margin-bottom: var(--space-8);
	}
	.count {
		margin-left: 4px;
		font-weight: 400;
		color: var(--muted);
	}
	/* An index, not a wall of cards: one panel per group, one row per document. */
	.index {
		list-style: none;
		margin: 0;
		padding: 4px 0;
	}
	.index li + li {
		border-top: 1px solid var(--rule);
	}
	.row-link {
		display: grid;
		grid-template-columns: 36px minmax(0, 1fr) auto 16px;
		gap: 16px;
		align-items: center;
		padding: 14px 20px;
		color: var(--ink);
		text-decoration: none;
		transition: background-color var(--dur-fast) ease;
	}
	.row-link.ghost {
		grid-template-columns: 36px minmax(0, 1fr);
	}
	@media (hover: hover) {
		a.row-link:hover {
			background: #f6f7f6;
		}
		a.row-link:hover .go {
			color: var(--ink);
			transform: translateX(2px);
		}
	}
	.row-link:focus-visible {
		outline-offset: -2px;
	}
	.icon {
		display: grid;
		place-items: center;
		width: 36px;
		height: 36px;
		border-radius: var(--r-control);
		background: var(--desk);
		color: var(--ink-2);
	}
	.text {
		display: grid;
		gap: 3px;
		min-width: 0;
	}
	.text strong {
		font-size: 15.5px;
		font-weight: 600;
	}
	.summary {
		color: var(--ink-2);
		font-size: 14px;
	}
	.when {
		white-space: nowrap;
	}
	.go {
		display: grid;
		color: var(--muted);
		transition:
			color var(--dur-fast) ease,
			transform var(--dur-fast) var(--ease-out);
	}
	@media (max-width: 700px) {
		.row-link {
			grid-template-columns: 36px minmax(0, 1fr) 16px;
			padding: 12px 14px;
		}
		.when {
			display: none;
		}
	}
</style>
