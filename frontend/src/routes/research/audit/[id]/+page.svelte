<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import { page } from '$app/state';
	import { api } from '#lib/api.js';
	import { t } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { act, notify } from '#lib/toast.svelte.js';
	import type { AuditLabel, AuditWorkspace } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	const id = $derived(page.params.id ?? '');
	let ws = $state<AuditWorkspace | null>(null);
	let error = $state('');
	let selected = $state('');
	let label = $state<AuditLabel | ''>('');
	let note = $state('');
	let busy = $state(false);

	async function load() {
		try {
			ws = await api<AuditWorkspace>(`/api/audit/set?id=${encodeURIComponent(id)}`);
			if (!selected && ws.rows.length) pick((ws.rows.find((r) => !r.mine) ?? ws.rows[0]).item_id);
		} catch (e) {
			error = (e as Error).message;
		}
	}
	$effect(() => {
		if (canReview(session.account) && id) load();
	});

	const done = $derived(ws ? ws.rows.filter((r) => r.mine).length : 0);
	const index = $derived(ws ? ws.rows.findIndex((r) => r.item_id === selected) : -1);
	const current = $derived(ws && index >= 0 ? ws.rows[index] : null);
	const others = $derived(ws ? Object.entries(ws.labelled).filter(([who]) => who !== session.account?.username) : []);
	const normLines = (norm: string) => norm.split('\n').filter(Boolean).map((line) => {
		const at = line.indexOf(':');
		return at > 0 ? { name: line.slice(0, at), value: line.slice(at + 1).trim() } : { name: '', value: line };
	});

	function pick(itemId: string) {
		selected = itemId;
		const row = ws?.rows.find((r) => r.item_id === itemId);
		label = row?.mine?.label ?? '';
		note = row?.mine?.note ?? '';
	}

	async function save(next: boolean) {
		if (!ws || !current || !label) return;
		busy = true;
		const ok = await act(async () => {
			const saved = await api<{ label: AuditLabel; note: string }>('/api/audit/label', { set_id: id, item_id: current.item_id, label, note });
			current.mine = { label: saved.label, note: saved.note, updated_at: new Date().toISOString() };
			notify({ key: 'audit.saved', params: { n: index + 1 } });
		});
		busy = false;
		if (ok && next && ws) {
			const after = ws.rows.slice(index + 1).find((r) => !r.mine) ?? ws.rows[index + 1];
			if (after) pick(after.item_id);
		}
	}

	// Number keys 1-5 pick a label; Ctrl+Enter saves and moves on. Ignored while typing a note.
	function keys(event: KeyboardEvent) {
		if (!ws || !current) return;
		const typing = (event.target as HTMLElement).closest('textarea, input');
		if (event.key === 'Enter' && (event.ctrlKey || event.metaKey) && label) {
			event.preventDefault();
			save(true);
		} else if (!typing && !event.ctrlKey && !event.metaKey && !event.altKey && /^[1-5]$/.test(event.key)) {
			label = ws.labels[Number(event.key) - 1];
		}
	}
</script>

<svelte:window onkeydown={keys} />
<svelte:head><title>{ws?.name ?? t('audit.title')} · Lexora</title></svelte:head>

<div class="page">
	{#if !canReview(session.account)}
		<h1 class="title">{t('common.forbidden.title')}</h1>
	{:else if error}
		<p class="notice error" role="alert">{error}</p>
	{:else if !ws}
		<p class="muted">{t('common.loading')}</p>
	{:else}
		<p class="crumb"><a href="/research/audit"><Icon name="back" size={16} />{t('audit.title')}</a></p>
		<header class="page-head">
			<div>
				<h1 class="title serif">{ws.name}</h1>
				<p class="facts"><span>{t('audit.mine', { done, n: ws.rows.length })}</span><span>{t('audit.blind')}</span></p>
			</div>
			<div class="row">
				<a class="btn quiet" href="/docs/huong-dan-kiem-tra-quy-pham"><Icon name="doc" size={16} />{t('audit.guide')}</a>
				{#if ws.can_score}<a class="btn" href="/research/audit/{id}/score">{t('audit.score')}</a>{/if}
			</div>
		</header>

		<div class="cols">
			<section class="panel list" aria-labelledby="list-heading">
				<h2 class="heading" id="list-heading">{t('audit.rows')}</h2>
				<progress max={ws.rows.length} value={done} aria-label={t('audit.mine', { done, n: ws.rows.length })}></progress>
				<ol class="items">
					{#each ws.rows as row, i (row.item_id)}
						<li>
							<button type="button" class="item" aria-current={row.item_id === selected ? 'true' : undefined} onclick={() => pick(row.item_id)}>
								<span class="num">{i + 1}</span>
								<span class="text">{row.sentence}</span>
								<span class="tag">{#if row.mine}<span class="chip small label-{row.mine.label}">{t(`audit.label.${row.mine.label}` as MessageKey)}</span>{/if}</span>
							</button>
						</li>
					{/each}
				</ol>
				<div class="side-tools">
					{#each others as [who, info] (who)}
						<a class="btn small" href="/research/audit/{id}/compare?other={encodeURIComponent(who)}">{t('audit.compareWith', { name: info.name })}<Icon name="arrow" size={16} /></a>
					{/each}
					{#if done}<a class="btn quiet small" href="/api/audit/sheet.csv?id={id}&source={encodeURIComponent(session.account?.username ?? '')}" download><Icon name="download" size={16} />{t('audit.downloadMine')}</a>{/if}
				</div>
			</section>

			<section class="panel work" aria-labelledby="item-heading">
				{#if !current}
					<p class="muted">{t('audit.pickOne')}</p>
				{:else}
					<h2 class="heading" id="item-heading">{t('audit.rowN', { n: index + 1, total: ws.rows.length })}</h2>
					{#if current.context}
						<div class="block">
							<p class="label">{t('audit.context')}</p>
							<p class="context">{#each current.context.split('\n') as line, i (i)}<span>{line}</span>{/each}</p>
						</div>
					{/if}
					<div class="block">
						<p class="label">{t('audit.unit')}</p>
						<p class="unit serif">{current.unit_text}</p>
						{#if current.sentence && current.sentence !== current.unit_text.trim()}
							<p class="small"><span class="label">{t('audit.sentence')}</span> <mark>{current.sentence}</mark></p>
						{/if}
					</div>
					<div class="block norm">
						<p class="label">{t('audit.norm')}</p>
						<dl>
							{#each normLines(current.norm) as line, i (i)}<dt>{line.name}</dt><dd>{line.value}</dd>{/each}
						</dl>
					</div>

					<fieldset class="choices-grid" disabled={busy}>
						<legend class="label">{t('audit.pick')}</legend>
						{#each ws.labels as value, i (value)}
							<label class="opt" class:on={label === value}>
								<input type="radio" name="audit-label" {value} bind:group={label} />
								<span class="key" aria-hidden="true">{i + 1}</span>
								<span><strong>{t(`audit.label.${value}` as MessageKey)}</strong><span class="small muted">{t(`audit.label.${value}.d` as MessageKey)}</span></span>
							</label>
						{/each}
					</fieldset>
					<label class="field"><span>{t('audit.note')}</span><textarea rows="2" bind:value={note} placeholder={t('audit.notePh')}></textarea></label>
					<div class="row actions">
						<span class="small muted">{t('audit.keys')}</span>
						<span class="spacer"></span>
						<button type="button" class="btn" disabled={busy || !label} onclick={() => save(false)}>{t('audit.save')}</button>
						<button type="button" class="btn primary" disabled={busy || !label} onclick={() => save(true)}>{t('audit.saveNext')}<Icon name="arrow" /></button>
					</div>
				{/if}
			</section>
		</div>
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
	.facts {
		display: flex;
		flex-wrap: wrap;
		gap: 6px 18px;
		margin-top: 10px;
		color: var(--ink-2);
	}
	.cols {
		display: grid;
		grid-template-columns: minmax(260px, 0.8fr) minmax(0, 1.7fr);
		gap: 20px;
		align-items: start;
	}
	.panel {
		display: grid;
		gap: 12px;
	}
	.list {
		position: sticky;
		top: calc(var(--topbar) + 16px);
		max-height: calc(100vh - var(--topbar) - 32px);
		grid-template-rows: auto auto 1fr auto;
		overflow: hidden;
	}
	progress {
		width: 100%;
	}
	.items {
		list-style: none;
		margin: 0 -8px;
		padding: 0;
		overflow: auto;
	}
	.item {
		width: 100%;
		display: grid;
		grid-template-columns: 2.2rem minmax(0, 1fr) auto;
		gap: 8px;
		align-items: start;
		text-align: left;
		padding: 8px;
		border: 0;
		border-radius: var(--r-control);
		background: none;
		font: inherit;
		color: inherit;
		cursor: pointer;
	}
	.item:hover,
	.item[aria-current='true'] {
		background: var(--desk);
	}
	.item[aria-current='true'] .num {
		color: var(--ink);
		font-weight: 600;
	}
	.num {
		color: var(--muted);
		font-variant-numeric: tabular-nums;
	}
	.text {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	.chip.small {
		font-size: 11.5px;
		padding: 0 7px;
		white-space: nowrap;
	}
	.label-sai {
		color: var(--reject);
		border-color: currentColor;
	}
	.label-dung {
		color: var(--approve);
		border-color: currentColor;
	}
	.side-tools {
		display: grid;
		gap: 8px;
		padding-top: 10px;
		border-top: 1px solid var(--rule);
	}
	.side-tools .btn {
		justify-content: flex-start;
	}
	.block {
		display: grid;
		gap: 4px;
	}
	.block p {
		margin: 0;
	}
	.context {
		display: grid;
		gap: 2px;
		color: var(--ink-2);
		max-width: 80ch;
	}
	.unit {
		font-size: 1.2rem;
		line-height: 1.6;
		max-width: 72ch;
	}
	mark {
		background: var(--hl-object);
		padding: 0 3px;
		border-radius: 3px;
	}
	.norm dl {
		display: grid;
		grid-template-columns: minmax(110px, max-content) minmax(0, 1fr);
		gap: 6px 14px;
		margin: 0;
		padding: 12px 14px;
		background: var(--desk);
		border-radius: var(--r-control);
	}
	.norm dt {
		color: var(--muted);
	}
	.norm dd {
		margin: 0;
		overflow-wrap: anywhere;
	}
	.choices-grid {
		display: grid;
		gap: 8px;
		border: 0;
		padding: 0;
		margin: 0;
	}
	.opt {
		display: grid;
		grid-template-columns: auto auto minmax(0, 1fr);
		gap: 10px;
		align-items: start;
		padding: 10px 12px;
		border: 1px solid var(--rule);
		border-radius: var(--r-control);
		cursor: pointer;
	}
	.opt:hover {
		border-color: var(--ink-2);
	}
	.opt.on {
		border-color: var(--graphite);
		background: var(--desk);
	}
	.opt input {
		margin-top: 3px;
	}
	.opt > span:last-child {
		display: grid;
		gap: 2px;
	}
	.key {
		display: grid;
		place-items: center;
		width: 22px;
		height: 22px;
		border-radius: 4px;
		border: 1px solid var(--rule-strong);
		font-size: 12px;
		color: var(--muted);
	}
	.actions {
		gap: 10px;
		align-items: center;
		flex-wrap: wrap;
	}
	.spacer {
		flex: 1;
	}
	@media (max-width: 1000px) {
		.cols {
			grid-template-columns: 1fr;
		}
		.list {
			position: static;
			max-height: 380px;
		}
	}
</style>
