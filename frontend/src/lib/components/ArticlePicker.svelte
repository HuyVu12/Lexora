<script lang="ts">
	import Icon from './Icon.svelte';
	import { t } from '#lib/i18n/index.svelte.js';
	import type { OutlineArticle } from '#lib/types.js';

	// Choose articles of a long statute, grouped by chapter. Blocked articles show why and cannot be chosen.
	let { articles, selected = $bindable([]), max = 60 }: { articles: OutlineArticle[]; selected: string[]; max?: number } = $props();

	let filter = $state('');
	const groups = $derived.by(() => {
		const f = filter.trim().toLowerCase();
		const list: { chapter: string; items: OutlineArticle[] }[] = [];
		for (const a of articles) {
			if (f && !`${a.heading} ${a.chapter ?? ''} ${a.section ?? ''}`.toLowerCase().includes(f)) continue;
			const chapter = a.chapter ?? t('import.pick.noChapter');
			if (list.at(-1)?.chapter !== chapter) list.push({ chapter, items: [] });
			list.at(-1)!.items.push(a);
		}
		return list;
	});
	const choosable = (items: OutlineArticle[]) => items.filter((a) => !a.blocked).map((a) => a.id);
	const allIn = (items: OutlineArticle[]) => choosable(items).length > 0 && choosable(items).every((id) => selected.includes(id));
	function toggleGroup(items: OutlineArticle[]) {
		const ids = choosable(items);
		selected = allIn(items) ? selected.filter((id) => !ids.includes(id)) : [...new Set([...selected, ...ids])];
	}
	const blockedCount = $derived(articles.filter((a) => a.blocked).length);
</script>

<div class="picker">
	<div class="row bar">
		<label class="field filter"><span>{t('import.pick.filter')}</span><input type="search" bind:value={filter} placeholder={t('import.pick.filterPh')} /></label>
		<p class="count small" class:over={selected.length > max} aria-live="polite">{t('import.pick.count', { n: selected.length, max })}</p>
		{#if selected.length}<button type="button" class="btn quiet small" onclick={() => (selected = [])}>{t('import.pick.clear')}</button>{/if}
	</div>
	{#if blockedCount}<p class="small muted"><Icon name="warn" size={14} /> {t('import.pick.blockedNote', { n: blockedCount })}</p>{/if}
	<div class="list">
		{#each groups as g (g.chapter)}
			<section>
				<label class="chapter check">
					<input type="checkbox" checked={allIn(g.items)} disabled={!choosable(g.items).length} onchange={() => toggleGroup(g.items)} />
					<span>{g.chapter}</span>
				</label>
				<ul>
					{#each g.items as a (a.id)}
						<li class:blocked={a.blocked}>
							<label class="check">
								<input type="checkbox" value={a.id} bind:group={selected} disabled={a.blocked} />
								<span><span class="serif">{a.heading}</span>{#if a.section}<span class="small muted"> · {a.section}</span>{/if}
									{#if a.blocked}<span class="small reason">{t('import.pick.blocked')}</span>{/if}</span>
							</label>
						</li>
					{/each}
				</ul>
			</section>
		{:else}
			<p class="small muted">{t('import.pick.none')}</p>
		{/each}
	</div>
</div>

<style>
	.picker {
		display: grid;
		gap: 10px;
	}
	.bar {
		gap: 14px;
		align-items: flex-end;
		flex-wrap: wrap;
	}
	.filter {
		flex: 1;
		min-width: 220px;
	}
	.count {
		margin: 0 0 10px;
		color: var(--ink-2);
	}
	.count.over {
		color: var(--reject);
		font-weight: 600;
	}
	.list {
		max-height: 420px;
		overflow: auto;
		border: 1px solid var(--rule);
		border-radius: var(--r-control);
		background: var(--paper);
	}
	section + section {
		border-top: 1px solid var(--rule);
	}
	.chapter {
		position: sticky;
		top: 0;
		padding: 8px 12px;
		background: var(--desk);
		font-weight: 600;
		font-size: 14px;
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	li {
		padding: 6px 12px 6px 34px;
	}
	li.blocked {
		color: var(--muted);
	}
	.reason {
		display: block;
		color: var(--attention);
	}
</style>
