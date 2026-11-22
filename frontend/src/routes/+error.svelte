<script lang="ts">
	import { page } from '$app/state';
	import Icon from '#lib/components/Icon.svelte';
	import { t } from '#lib/i18n/index.svelte.js';
	import { reveal } from '#lib/motion.js';

	// Errors read like an article of the statute this app is about: "Article 404. The page does not exist".
	const missing = $derived(page.status === 404);
</script>

<svelte:head><title>{missing ? t('error.404.title') : t('error.other.title')} · Lexora</title></svelte:head>

<div class="page error-page">
	<article class="sheet statute" {@attach reveal({ y: 10 })}>
		<p class="article serif">{t('error.article', { code: page.status })}</p>
		<h1 class="title">{missing ? t('error.404.title') : t('error.other.title')}</h1>
		<ol class="clauses serif">
			<li>{missing ? t('error.404.clause1') : t('error.other.clause1')}</li>
			<li>{missing ? t('error.404.clause2') : t('error.other.clause2')}</li>
		</ol>
		{#if !missing && page.error?.message}<p class="small muted detail"><code>{page.error.message}</code></p>{/if}
		<div class="row actions">
			<a class="btn primary" href="/"><Icon name="back" />{t('common.toHome')}</a>
			{#if missing}
				<button type="button" class="btn" onclick={() => history.back()}>{t('common.back')}</button>
			{:else}
				<button type="button" class="btn" onclick={() => location.reload()}>{t('error.reload')}</button>
			{/if}
		</div>
		<p class="pencil path">{page.url.pathname}</p>
	</article>
</div>

<style>
	.error-page {
		display: grid;
		place-items: start center;
		padding-top: clamp(32px, 9vh, 96px);
	}
	.statute {
		width: min(620px, 100%);
		padding: 40px 44px 32px;
		display: grid;
		gap: 14px;
	}
	.article {
		font-size: 15px;
		font-weight: 600;
		letter-spacing: 0.02em;
		color: var(--muted);
	}
	.article::after {
		content: '';
		display: block;
		width: 48px;
		height: 6px;
		margin-top: 10px;
		border-radius: 2px;
		background: var(--hl-actor);
	}
	.clauses {
		margin: 4px 0 0;
		padding-left: 22px;
		display: grid;
		gap: 6px;
		font-size: 17px;
		line-height: 1.7;
		color: var(--ink-2);
	}
	.detail code {
		overflow-wrap: anywhere;
	}
	.actions {
		margin-top: 10px;
		gap: 10px;
	}
	.path {
		margin-top: 8px;
		padding-top: 14px;
		border-top: 1px solid var(--rule);
		overflow-wrap: anywhere;
	}
	@media (max-width: 640px) {
		.statute {
			padding: 28px 22px 24px;
		}
	}
</style>
