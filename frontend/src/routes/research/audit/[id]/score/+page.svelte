<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import { page } from '$app/state';
	import { api } from '#lib/api.js';
	import { t } from '#lib/i18n/index.svelte.js';
	import { session, canMonitor } from '#lib/session.svelte.js';
	import type { AuditScore, AuditSetSummary } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	const id = $derived(page.params.id ?? '');
	let summary = $state<AuditSetSummary | null>(null);
	let source = $state('final');
	let score = $state<AuditScore | null>(null);
	let error = $state('');

	$effect(() => {
		if (!canMonitor(session.account) || !id) return;
		api<{ sets: AuditSetSummary[] }>('/api/audit').then((v) => (summary = v.sets.find((s) => s.id === id) ?? null)).catch((e) => (error = e.message));
	});
	$effect(() => {
		if (!canMonitor(session.account) || !id) return;
		const wanted = source;
		score = null;
		api<AuditScore>(`/api/audit/score?id=${encodeURIComponent(id)}&source=${encodeURIComponent(wanted)}`)
			.then((v) => (score = v))
			.catch((e) => (error = e.message));
	});
	const pct = (v: number | null) => (v === null ? '-' : `${(v * 100).toFixed(1)}%`);
	const LABELS = ['sai', 'dien_dat', 'dung_ngu_canh', 'dung', 'khong_ro'];
</script>

<svelte:head><title>{t('audit.score')} · Lexora</title></svelte:head>

<div class="page">
	{#if !canMonitor(session.account)}
		<h1 class="title">{t('common.forbidden.title')}</h1>
		<p class="lead">{t('audit.scoreForbidden')}</p>
	{:else}
		<p class="crumb"><a href="/research/audit"><Icon name="back" size={16} />{t('audit.title')}</a></p>
		<header class="page-head">
			<div>
				<h1 class="title">{t('audit.score')}{summary ? `: ${summary.name}` : ''}</h1>
				<p class="lead">{t('audit.scoreLead')}</p>
			</div>
			<label class="field source"><span>{t('audit.scoreSource')}</span>
				<select bind:value={source}>
					<option value="final">{t('audit.scoreFinal', { n: summary?.adjudicated ?? 0 })}</option>
					{#each Object.entries(summary?.labelled ?? {}) as [who, v] (who)}<option value={who}>{v.name} (@{who}): {v.n}</option>{/each}
				</select>
			</label>
		</header>
		<p class="notice warn small">{t('audit.scoreBlind')}</p>
		{#if error}
			<p class="notice error" role="alert">{error}</p>
		{:else if !score}
			<p class="muted">{t('common.loading')}</p>
		{:else if !score.labelled}
			<p class="muted">{t('audit.scoreEmpty')}</p>
		{:else}
			<section class="panel">
				<div class="table-wrap">
					<table class="table">
						<thead>
							<tr>
								<th scope="col">{t('dev.col.model')}</th>
								<th scope="col">{t('audit.scoreDecision')}</th>
								<th scope="col" class="num">{t('audit.scoreLabelled')}</th>
								{#each LABELS as l (l)}<th scope="col" class="num">{t(`audit.label.${l}` as MessageKey)}</th>{/each}
								<th scope="col" class="num">{t('audit.scoreWrong')}</th>
							</tr>
						</thead>
						<tbody>
							{#each Object.entries(score.by_model) as [model, groups] (model)}
								{#each Object.entries(groups) as [decision, g] (decision)}
									<tr>
										<th scope="row"><code>{model}</code></th>
										<td>{t(`audit.decision.${decision}` as MessageKey)}</td>
										<td class="num">{g.labelled}/{g.items}</td>
										{#each LABELS as l (l)}<td class="num">{g.labels[l] ?? 0}</td>{/each}
										<td class="num"><strong>{pct(g.wrong_rate.value)}</strong> <span class="muted small">n={g.wrong_rate.n}</span></td>
									</tr>
								{/each}
							{/each}
						</tbody>
					</table>
				</div>
				<p class="small muted">{t('audit.scoreNote')}</p>
			</section>
		{/if}
	{/if}
</div>

<style>
	.crumb {
		margin: 0 0 8px;
	}
	.crumb a {
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}
	.source {
		min-width: 260px;
		margin: 0;
	}
	.panel {
		display: grid;
		gap: 12px;
		margin-top: 16px;
	}
	.table-wrap {
		overflow-x: auto;
	}
	.table th[scope='row'] {
		font-weight: 500;
		color: var(--ink);
		font-size: 14px;
	}
	.table td.num {
		white-space: nowrap;
	}
	.table tr:last-child th {
		border-bottom: 0;
	}
</style>
