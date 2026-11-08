<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import { page } from '$app/state';
	import { api } from '#lib/api.js';
	import { t } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { act, notify } from '#lib/toast.svelte.js';
	import type { AuditCompare, AuditLabel } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	const LABELS: AuditLabel[] = ['sai', 'dien_dat', 'dung_ngu_canh', 'dung', 'khong_ro'];
	const id = $derived(page.params.id ?? '');
	const other = $derived(page.url.searchParams.get('other') ?? '');
	let data = $state<AuditCompare | null>(null);
	let error = $state('');
	let filter = $state<'disagree' | 'open' | 'all'>('disagree');
	let choice = $state<Record<string, AuditLabel | ''>>({});
	let notes = $state<Record<string, string>>({});
	let busy = $state(false);

	async function load() {
		try {
			data = await api<AuditCompare>(`/api/audit/compare?id=${encodeURIComponent(id)}&other=${encodeURIComponent(other)}`);
		} catch (e) {
			error = (e as Error).message;
		}
	}
	$effect(() => {
		if (canReview(session.account) && id && other) load();
	});

	const shown = $derived(
		data
			? data.items
					.map((item, i) => ({ item, n: i + 1 }))
					.filter(({ item }) => filter === 'all' || (filter === 'open' ? !item.final : !item.agree && !item.final))
			: []
	);
	const agreedOpen = $derived(data ? data.items.filter((i) => i.agree && !i.final).length : 0);
	const kappa = (v: number | null) => (v === null ? '-' : v.toFixed(2));
	const name = (l: AuditLabel) => t(`audit.label.${l}` as MessageKey);

	async function acceptAgreed() {
		busy = true;
		await act(async () => {
			const r = await api<{ accepted: number }>('/api/audit/accept-agreed', { set_id: id, other });
			notify({ key: 'audit.cmp.accepted', params: { n: r.accepted } });
			await load();
		});
		busy = false;
	}
	async function decide(itemId: string, label: AuditLabel | '', n: number) {
		if (!label) return;
		busy = true;
		await act(async () => {
			await api('/api/audit/adjudicate', { set_id: id, item_id: itemId, label, note: notes[itemId] ?? '' });
			notify({ key: 'audit.cmp.decided', params: { n } });
			await load();
		});
		busy = false;
	}
</script>

<svelte:head><title>{t('audit.cmp.title')} · Lexora</title></svelte:head>

<div class="page">
	{#if !canReview(session.account)}
		<h1 class="title">{t('common.forbidden.title')}</h1>
	{:else if error}
		<p class="notice error" role="alert">{error}</p>
	{:else if !data}
		<p class="muted">{t('common.loading')}</p>
	{:else}
		<p class="crumb"><a href="/research/audit/{id}"><Icon name="back" size={16} />{data.set.name}</a></p>
		<header class="page-head">
			<div>
				<h1 class="title">{t('audit.cmp.title')}</h1>
				<p class="lead">{t('audit.cmp.lead', { a: data.first.name, b: data.second.name })}</p>
			</div>
		</header>

		<section class="panel metrics" aria-label={t('audit.cmp.metrics')}>
			<div><span class="label">{t('audit.cmp.kappaLabels')}</span><strong>{kappa(data.agreement.labels.kappa)}</strong><span class="small muted">n = {data.agreement.labels.n}</span></div>
			<div><span class="label">{t('audit.cmp.kappaWrong')}</span><strong>{kappa(data.agreement.wrong_or_not.kappa)}</strong><span class="small muted">n = {data.agreement.wrong_or_not.n}</span></div>
			<div><span class="label">{t('audit.cmp.progress')}</span><strong>{data.set.first_labelled} / {data.set.second_labelled}</strong><span class="small muted">{t('audit.cmp.of', { n: data.set.items })}</span></div>
			<div><span class="label">{t('audit.cmp.final')}</span><strong>{data.set.adjudicated}</strong><span class="small muted">{t('audit.cmp.of', { n: data.set.items })}</span></div>
		</section>
		<p class="small muted note">{t('audit.cmp.kappaNote')}</p>

		<div class="row bar">
			<div class="segmented" role="group" aria-label={t('audit.cmp.filter')}>
				{#each ['disagree', 'open', 'all'] as const as f (f)}
					<button type="button" aria-pressed={filter === f} onclick={() => (filter = f)}>{t(`audit.cmp.filter.${f}` as MessageKey)}</button>
				{/each}
			</div>
			<span class="spacer"></span>
			<button type="button" class="btn" disabled={busy || !agreedOpen} onclick={acceptAgreed}>{t('audit.cmp.acceptAgreed', { n: agreedOpen })}</button>
		</div>

		{#if !shown.length}
			<p class="muted">{t('audit.cmp.none')}</p>
		{:else}
			<ol class="cards">
				{#each shown as { item, n } (item.item_id)}
					<li class="panel card">
						<p class="small muted">{t('audit.rowN', { n, total: data.set.items })}{#if item.final} · <strong class="done">{t('audit.cmp.decidedBy', { label: name(item.final.label), who: item.final.decided_by })}</strong>{/if}</p>
						<p class="serif unit">{item.unit_text}</p>
						<pre class="norm">{item.norm}</pre>
						<div class="sides">
							{#each [{ who: data.first.name, l: item.first }, { who: data.second.name, l: item.second }] as side, i (i)}
								<div class="side">
									<span class="label">{side.who}</span>
									{#if side.l}<strong>{name(side.l.label)}</strong>{#if side.l.note}<span class="small muted">{side.l.note}</span>{/if}{:else}<span class="muted">{t('audit.cmp.notLabelled')}</span>{/if}
								</div>
							{/each}
						</div>
						<div class="decide">
							<label class="field"><span>{t('audit.cmp.finalLabel')}</span>
								<select bind:value={choice[item.item_id]}>
									<option value="">{item.final ? name(item.final.label) : t('audit.cmp.choose')}</option>
									{#each LABELS as l (l)}<option value={l}>{name(l)}</option>{/each}
								</select>
							</label>
							<label class="field grow"><span>{t('audit.note')}</span><input class="input" bind:value={notes[item.item_id]} placeholder={item.final?.note ?? ''} /></label>
							<button type="button" class="btn primary" disabled={busy || !choice[item.item_id]} onclick={() => decide(item.item_id, choice[item.item_id] ?? '', n)}>{t('audit.cmp.decide')}</button>
						</div>
					</li>
				{/each}
			</ol>
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
	.metrics {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
		gap: 16px;
	}
	.metrics div {
		display: grid;
		gap: 2px;
	}
	.metrics strong {
		font: 600 24px/1.2 var(--serif);
		font-variant-numeric: tabular-nums;
	}
	.note {
		margin: 8px 0 18px;
	}
	.bar {
		gap: 10px;
		margin-bottom: 14px;
	}
	.spacer {
		flex: 1;
	}
	.cards {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 12px;
	}
	.card {
		display: grid;
		gap: 10px;
	}
	.card p {
		margin: 0;
	}
	.done {
		color: var(--approve);
	}
	.unit {
		font-size: 1.1rem;
		line-height: 1.55;
	}
	.norm {
		margin: 0;
		padding: 10px 12px;
		border-radius: var(--r-control);
		background: var(--desk);
		font: inherit;
		font-size: 14px;
		white-space: pre-wrap;
	}
	.sides {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 12px;
	}
	.side {
		display: grid;
		gap: 2px;
		padding: 10px 12px;
		border: 1px solid var(--rule);
		border-radius: var(--r-control);
	}
	.decide {
		display: flex;
		flex-wrap: wrap;
		gap: 10px;
		align-items: end;
	}
	.decide .field {
		margin: 0;
	}
	.grow {
		flex: 1;
		min-width: 200px;
	}
	@media (max-width: 700px) {
		.sides {
			grid-template-columns: 1fr;
		}
	}
</style>
