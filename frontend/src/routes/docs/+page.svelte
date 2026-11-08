<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import { api } from '#lib/api.js';
	import { t } from '#lib/i18n/index.svelte.js';
	import { session } from '#lib/session.svelte.js';
	import type { DocEntry } from '#lib/types.js';

	let documents = $state<DocEntry[] | null>(null);
	let error = $state('');
	let query = $state('');

	$effect(() => {
		if (session.account)
			api<{ documents: DocEntry[] }>('/api/docs')
				.then((v) => (documents = v.documents))
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
			<p class="lead">{t('docs.lead')}</p>
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
		<p class="muted">{t('common.loading')}</p>
	{:else if !documents.length}
		<p class="muted">{t('docs.empty')}</p>
	{:else if !shown.length}
		<p class="muted">{t('docs.noMatch')}</p>
	{:else}
		{#each groups as group (group.category)}
			<section class="group" aria-labelledby="cat-{group.category}">
				<h2 class="label" id="cat-{group.category}">{group.category}</h2>
				<ul class="cards">
					{#each group.items as doc (doc.slug)}
						<li>
							<a class="card" href="/docs/{doc.slug}">
								<span class="icon" aria-hidden="true"><Icon name="doc" size={20} /></span>
								<span class="text">
									<strong>{doc.title}</strong>
									{#if doc.summary}<span class="summary">{doc.summary}</span>{/if}
									{#if doc.updated}<span class="small muted">{t('docs.updated', { date: date(doc.updated) })}</span>{/if}
								</span>
								<Icon name="arrow" size={16} />
							</a>
						</li>
					{/each}
				</ul>
			</section>
		{/each}
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
		margin-bottom: 28px;
	}
	.cards {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
		gap: 12px;
	}
	.card {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto;
		gap: 14px;
		align-items: start;
		height: 100%;
		padding: 18px;
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: var(--r-panel);
		color: var(--ink);
		text-decoration: none;
		transition: border-color 0.15s var(--ease-out);
	}
	.card:hover {
		border-color: var(--ink-2);
	}
	.card:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	.card > :global(svg:last-child) {
		color: var(--muted);
		margin-top: 2px;
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
		gap: 4px;
	}
	.text strong {
		font-size: 15.5px;
		font-weight: 600;
	}
	.summary {
		color: var(--ink-2);
		font-size: 14px;
	}
	@media (prefers-reduced-motion: reduce) {
		.card {
			transition: none;
		}
	}
</style>
