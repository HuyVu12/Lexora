<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import Skeleton from '#lib/components/Skeleton.svelte';
	import { page } from '$app/state';
	import { api } from '#lib/api.js';
	import { t } from '#lib/i18n/index.svelte.js';
	import { session } from '#lib/session.svelte.js';
	import { render } from '#lib/markdown.js';
	import type { DocEntry } from '#lib/types.js';

	const slug = $derived(page.params.slug ?? '');
	let doc = $state<(DocEntry & { markdown: string }) | null>(null);
	let error = $state('');
	let active = $state('');

	$effect(() => {
		const wanted = slug;
		if (!session.account || !wanted) return;
		doc = null;
		error = '';
		api<DocEntry & { markdown: string }>(`/api/docs/${encodeURIComponent(wanted)}`)
			.then((v) => (doc = v))
			.catch((e) => (error = e.message));
	});
	const rendered = $derived(doc ? render(doc.markdown) : null);
	const date = (value: string | null) => (value ? value.split('-').reverse().join('/') : '');

	// Highlight the section being read in the table of contents.
	$effect(() => {
		if (!rendered) return;
		const targets = rendered.headings.map((h) => document.getElementById(h.id)).filter((el): el is HTMLElement => !!el);
		const observer = new IntersectionObserver(
			(entries) => {
				const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
				if (visible.length) active = visible[0].target.id;
			},
			{ rootMargin: '-70px 0px -70% 0px' }
		);
		targets.forEach((el) => observer.observe(el));
		if (location.hash) document.getElementById(decodeURIComponent(location.hash.slice(1)))?.scrollIntoView();
		return () => observer.disconnect();
	});
</script>

<svelte:head><title>{doc?.title ?? t('docs.title')} · Lexora</title></svelte:head>

<div class="page reader">
	<p class="crumb"><a href="/docs"><Icon name="back" size={16} />{t('docs.back')}</a></p>
	{#if error}
		<p class="notice error" role="alert">{error}</p>
	{:else if !doc || !rendered}
		<div class="layout" aria-busy="true">
			<span class="visually-hidden" role="status">{t('common.loading')}</span>
			<div class="sheet doc ghost" aria-hidden="true">
				<div class="ghost-head"><Skeleton width="110px" height="11px" /><Skeleton width="70%" height="30px" /><Skeleton width="90%" height="14px" /></div>
				{#each [5, 4, 6] as n, i (i)}
					<Skeleton width="40%" height="20px" />
					<Skeleton lines={n} height="13px" gap="13px" last="55%" />
				{/each}
			</div>
		</div>
	{:else}
		<div class="layout">
			<article class="sheet doc">
				<header>
					<p class="label">{doc.category}</p>
					<h1 class="title">{doc.title}</h1>
					{#if doc.summary}<p class="lead">{doc.summary}</p>{/if}
					{#if doc.updated}<p class="small muted">{t('docs.updated', { date: date(doc.updated) })}</p>{/if}
				</header>
				<!-- The renderer escapes every character of the document before adding its own tags. -->
				<div class="prose">{@html rendered.html}</div>
			</article>
			{#if rendered.headings.length > 2}
				<nav class="toc" aria-label={t('docs.toc')}>
					<p class="label">{t('docs.toc')}</p>
					<ol>
						{#each rendered.headings as h (h.id)}
							<li class:sub={h.level === 3}><a href="#{h.id}" aria-current={active === h.id ? 'location' : undefined}>{h.text}</a></li>
						{/each}
					</ol>
				</nav>
			{/if}
		</div>
	{/if}
</div>

<style>
	/* The sheet is as wide as a comfortable line of prose plus its margins; the contents sit beside it. */
	.reader {
		max-width: calc(840px + 240px + var(--space-10) + 64px);
	}
	.layout {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 240px;
		gap: var(--space-10);
		align-items: start;
	}
	.doc {
		padding: 44px 56px 60px;
		min-width: 0;
	}
	.ghost {
		display: grid;
		gap: 18px;
	}
	.ghost-head {
		display: grid;
		gap: 12px;
		padding-bottom: 20px;
		border-bottom: 1px solid var(--rule);
	}
	.doc header {
		display: grid;
		gap: 8px;
		padding-bottom: 20px;
		margin-bottom: 8px;
		border-bottom: 1px solid var(--rule);
	}
	.toc {
		position: sticky;
		top: calc(var(--topbar) + 20px);
		max-height: calc(100vh - var(--topbar) - 40px);
		overflow-y: auto;
		display: grid;
		gap: 8px;
		font-size: 13.5px;
	}
	.toc ol {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 2px;
		border-left: 1px solid var(--rule);
	}
	.toc a {
		display: block;
		padding: 4px 0 4px 12px;
		margin-left: -1px;
		border-left: 2px solid transparent;
		color: var(--ink-2);
		text-decoration: none;
	}
	.toc li.sub a {
		padding-left: 24px;
		font-size: 13px;
	}
	.toc a:hover {
		color: var(--ink);
	}
	.toc a[aria-current='location'] {
		color: var(--ink);
		font-weight: 600;
		border-left-color: var(--graphite);
	}
	.prose {
		max-width: 72ch;
		font-size: 15.5px;
		line-height: 1.7;
	}
	.prose :global(h2) {
		font: 600 22px/1.3 var(--serif);
		margin: 36px 0 10px;
		scroll-margin-top: calc(var(--topbar) + 16px);
	}
	.prose :global(h3) {
		font: 600 17px/1.35 var(--sans);
		margin: 26px 0 8px;
		scroll-margin-top: calc(var(--topbar) + 16px);
	}
	.prose :global(h4) {
		font: 600 15px/1.4 var(--sans);
		margin: 20px 0 6px;
	}
	.prose :global(p) {
		margin: 0 0 12px;
	}
	.prose :global(ul),
	.prose :global(ol) {
		margin: 0 0 14px;
		padding-left: 24px;
	}
	.prose :global(li) {
		margin: 4px 0;
	}
	.prose :global(li > ul),
	.prose :global(li > ol) {
		margin: 4px 0 0;
	}
	.prose :global(code) {
		font-size: 13.5px;
		padding: 1px 5px;
		border-radius: 4px;
		background: var(--desk);
		overflow-wrap: anywhere;
	}
	.prose :global(pre) {
		line-height: 1.45;
		margin: 0 0 14px;
		padding: 14px 16px;
		border-radius: var(--r-control);
		background: var(--desk);
		overflow-x: auto;
	}
	.prose :global(pre code) {
		padding: 0;
		background: none;
	}
	.prose :global(blockquote) {
		margin: 0 0 14px;
		padding: 12px 16px;
		border-radius: var(--r-control);
		background: #edf2fc;
		border: 1px solid #c9d7f3;
	}
	.prose :global(blockquote p:last-child) {
		margin-bottom: 0;
	}
	.prose :global(.md-table) {
		overflow-x: auto;
		margin: 0 0 16px;
	}
	.prose :global(table) {
		width: 100%;
		border-collapse: collapse;
		font-size: 14px;
		line-height: 1.5;
	}
	.prose :global(th),
	.prose :global(td) {
		padding: 8px 10px;
		border-bottom: 1px solid var(--rule);
		text-align: left;
		vertical-align: top;
	}
	.prose :global(th) {
		font-weight: 600;
		color: var(--ink-2);
		border-bottom-color: var(--rule-strong);
	}
	.prose :global(figure) {
		margin: 4px 0 20px;
		display: grid;
		gap: 8px;
	}
	.prose :global(figure img) {
		display: block;
		width: 100%;
		max-width: 820px;
		height: auto;
		border-radius: var(--r-panel);
		border: 1px solid var(--rule);
	}
	.prose :global(figcaption) {
		font-size: 13px;
		color: var(--muted);
	}
	.prose :global(hr) {
		border: 0;
		border-top: 1px solid var(--rule);
		margin: 28px 0;
	}
	@media (max-width: 1140px) {
		.reader {
			max-width: calc(840px + 64px);
		}
		.layout {
			grid-template-columns: minmax(0, 1fr);
		}
		.toc {
			display: none;
		}
	}
	@media (max-width: 700px) {
		.doc {
			padding: 24px 18px 32px;
		}
		/* Narrow screens scroll wide tables sideways instead of squeezing every column. */
		.prose :global(table) {
			min-width: 560px;
		}
	}
</style>
