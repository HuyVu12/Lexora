<script lang="ts">
	import Icon from './Icon.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDay } from '#lib/i18n/index.svelte.js';
	import { notify } from '#lib/toast.svelte.js';
	import type { CatalogEntry } from '#lib/types.js';

	// Offline catalog search; picking a result asks the page to fetch it from vbpl.vn.
	let {
		onpick,
		canFetch,
		added = new Set<string>(),
		busy = false
	}: { onpick: (entry: CatalogEntry) => void; canFetch: boolean; added?: Set<string>; busy?: boolean } = $props();

	let query = $state('');
	let results = $state<CatalogEntry[]>([]);
	let searching = $state(false);
	let ticket = 0;
	$effect(() => {
		const q = query.trim();
		if (q.length < 2) {
			results = [];
			return;
		}
		const mine = ++ticket;
		const timer = setTimeout(async () => {
			searching = true;
			try {
				const found = await api<{ results: CatalogEntry[] }>(`/api/catalog/search?limit=12&q=${encodeURIComponent(q)}`);
				if (mine === ticket) results = found.results;
			} catch (e) {
				if (mine === ticket) notify((e as Error).message, true);
			} finally {
				if (mine === ticket) searching = false;
			}
		}, 250);
		return () => clearTimeout(timer);
	});

	const tone = (name?: string | null) =>
		!name ? '' : /^Còn hiệu lực|^Chưa có hiệu lực/.test(name) ? 'ok' : /một phần/.test(name) ? 'partial' : 'gone';
</script>

<div class="catalog">
	<label class="field">
		<span>{t('corpus.search.label')}</span>
		<input type="search" bind:value={query} placeholder={t('corpus.search.ph')} autocomplete="off" />
		<span class="hint">{t('corpus.search.hint')}</span>
	</label>
	{#if searching}<p class="small muted" aria-live="polite">{t('common.loading')}</p>{/if}
	{#if results.length}
		<ul class="results" aria-label={t('corpus.search.results')}>
			{#each results as r (r.vbpl_id)}
				<li>
					<div class="result-main">
						<span class="serif">{r.title}</span>
						<span class="small muted">{[r.doc_type, r.doc_num, r.issue_date && formatDay(r.issue_date), r.agency].filter(Boolean).join(' · ')}</span>
						{#if r.effect_status}<span class="status {tone(r.effect_status)}" title={t('corpus.search.statusNote')}>{r.effect_status}*</span>{/if}
						{#if r.usually_no_articles}<span class="small no-articles"><Icon name="warn" size={14} />{t('corpus.search.noArticles')}</span>{/if}
					</div>
					{#if added.has(r.vbpl_id)}
						<span class="small muted done"><Icon name="check" size={16} />{t('corpus.search.inCorpus')}</span>
					{:else}
						<button type="button" class="btn small" disabled={busy || !canFetch} onclick={() => onpick(r)}>{t('corpus.fetch')}</button>
					{/if}
				</li>
			{/each}
		</ul>
		<p class="small muted">* {t('corpus.search.statusNote')}</p>
	{:else if query.trim().length >= 2 && !searching}
		<p class="small muted">{t('corpus.search.none')}</p>
	{/if}
</div>

<style>
	.catalog {
		display: grid;
		gap: 12px;
	}
	.results {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.results li {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 16px;
		padding: 12px 0;
		border-top: 1px solid var(--rule);
	}
	.results li:first-child {
		border-top: 0;
	}
	.result-main {
		display: grid;
		gap: 3px;
		min-width: 0;
	}
	.done {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		white-space: nowrap;
		color: var(--approve);
	}
	.no-articles {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		color: var(--attention);
	}
	.status {
		justify-self: start;
		font-size: 0.8rem;
		padding: 1px 8px;
		border-radius: 999px;
		border: 1px solid var(--rule);
		color: var(--ink-2);
	}
	.status.ok {
		background: var(--approve-soft);
		border-color: #b9dcc5;
		color: var(--approve);
	}
	.status.partial {
		background: var(--attention-soft);
		border-color: #f0d3a1;
		color: var(--attention);
	}
	.status.gone {
		background: var(--reject-soft);
		border-color: #f1c4bf;
		color: var(--reject);
	}
</style>
