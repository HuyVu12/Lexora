<script lang="ts">
	import { t, formatDate } from '#lib/i18n/index.svelte.js';
	import type { DevKb } from '#lib/types.js';

	let { data }: { data: DevKb } = $props();

	const undecided = $derived(data.drafts.reduce((sum, d) => sum + Math.max(0, d.claims - d.decided), 0));
	const approved = $derived(data.knowledge_bases.reduce((sum, k) => sum + (k.approved_claims ?? 0), 0));
	const labelled = (g: DevKb['gold_sets'][number]) => Object.entries(g.labelled).map(([who, n]) => `${who} ${n}`).join(', ') || '-';
</script>

<div class="dev-tiles">
	<div class="dev-tile"><span class="label">{t('dev.kb.bases')}</span><strong>{data.knowledge_bases.length}</strong><span class="small muted">{t('dev.kb.approved', { n: approved.toLocaleString() })}</span></div>
	<div class="dev-tile"><span class="label">{t('dev.kb.openDrafts')}</span><strong>{data.drafts.length}</strong></div>
	<div class="dev-tile" class:warn={undecided > 0}><span class="label">{t('dev.kb.undecided')}</span><strong>{undecided.toLocaleString()}</strong></div>
	<div class="dev-tile"><span class="label">{t('dev.kb.corpora')}</span><strong>{data.corpora.length}</strong></div>
</div>

<section class="panel" aria-labelledby="bases-heading">
	<h2 class="heading" id="bases-heading">{t('dev.kb.basesTitle')}</h2>
	{#if data.knowledge_bases.length}
		<div class="table-scroll">
			<table class="table">
				<thead><tr><th scope="col">{t('dev.kb.name')}</th><th scope="col">{t('dev.kb.class')}</th><th scope="col" class="num">{t('dev.kb.documents')}</th>
					<th scope="col" class="num">{t('dev.kb.revisions')}</th><th scope="col" class="num">{t('dev.kb.approvedCol')}</th><th scope="col">{t('dev.kb.updated')}</th></tr></thead>
				<tbody>
					{#each data.knowledge_bases as k (k.id)}
						<tr>
							<th scope="row"><a href="/kb/{k.id}">{k.name}</a>{#if k.archived_at}<span class="small muted"> {t('dev.kb.archived')}</span>{/if}</th>
							<td><span class="chip {k.data_class}">{k.data_class === 'public' ? t('dev.kb.public') : t('dev.kb.private')}</span></td>
							<td class="num">{k.documents}</td>
							<td class="num">{k.revisions}</td>
							<td class="num">{k.approved_claims}</td>
							<td>{k.updated_at ? formatDate(k.updated_at) : '-'}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{:else}
		<p class="small muted">{t('dev.kb.none')}</p>
	{/if}
</section>

<div class="dev-two">
	<section class="panel" aria-labelledby="drafts-heading">
		<h2 class="heading" id="drafts-heading">{t('dev.kb.draftsTitle')}</h2>
		{#if data.drafts.length}
			<ul class="dev-list">
				{#each data.drafts as d (d.id)}
					<li><span>{d.title}<span class="small muted block">{d.kb_name} · {formatDate(d.created_at)}{d.extraction_state !== 'done' ? ` · ${d.extraction_state}` : ''}</span></span>
						<strong class="num">{t('dev.kb.decided', { done: d.decided, total: d.claims })}</strong></li>
				{/each}
			</ul>
		{:else}
			<p class="small muted">{t('dev.kb.noDrafts')}</p>
		{/if}
	</section>
	<section class="panel" aria-labelledby="publish-heading">
		<h2 class="heading" id="publish-heading">{t('dev.kb.publishes')}</h2>
		{#if Object.keys(data.publishes_by_reviewer).length}
			<ul class="dev-list">{#each Object.entries(data.publishes_by_reviewer) as [who, n] (who)}<li><span>{who}</span><strong>{n}</strong></li>{/each}</ul>
		{:else}
			<p class="small muted">{t('dev.kb.noPublishes')}</p>
		{/if}
	</section>
</div>

<div class="dev-two">
	<section class="panel" aria-labelledby="qsets-heading">
		<h2 class="heading" id="qsets-heading">{t('dev.kb.questionSets')}</h2>
		{#if data.question_sets.length}
			<ul class="dev-list">{#each data.question_sets as q (q.id)}<li><a href="/research/questions/{q.id}">{q.name}</a><span class="small muted">{t('dev.kb.questions', { n: q.questions })}{q.frozen ? ` · ${t('dev.kb.frozen')}` : ''}</span></li>{/each}</ul>
		{:else}
			<p class="small muted">{t('dev.kb.noQuestionSets')}</p>
		{/if}
	</section>
	<section class="panel" aria-labelledby="gold-heading">
		<h2 class="heading" id="gold-heading">{t('dev.kb.goldSets')}</h2>
		{#if data.gold_sets.length}
			<ul class="dev-list">{#each data.gold_sets as g (g.id)}<li><a href="/research/gold/{g.id}">{g.name}</a><span class="small muted">{t('dev.kb.gold', { n: g.sentences, who: labelled(g), final: g.adjudicated })}</span></li>{/each}</ul>
		{:else}
			<p class="small muted">{t('dev.kb.noGold')}</p>
		{/if}
	</section>
</div>

<style>
	.block {
		display: block;
	}
</style>
