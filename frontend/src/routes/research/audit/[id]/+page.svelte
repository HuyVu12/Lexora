<script lang="ts">
	import Skeleton from '#lib/components/Skeleton.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import ItemRail from '#lib/components/ItemRail.svelte';
	import WorkspaceSkeleton from '#lib/components/WorkspaceSkeleton.svelte';
	import { rise, DUR } from '#lib/motion.js';
	import '#lib/components/workspace.css';
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
	// The extracted sentence is part of the unit text: mark it in place instead of printing it a second time.
	const hit = $derived.by(() => {
		if (!current?.sentence || current.sentence === current.unit_text.trim()) return null;
		const at = current.unit_text.indexOf(current.sentence);
		return at < 0 ? null : { before: current.unit_text.slice(0, at), after: current.unit_text.slice(at + current.sentence.length) };
	});
	const others = $derived(ws ? Object.entries(ws.labelled).filter(([who]) => who !== session.account?.username) : []);
	const normLines = (norm: string) => norm.split('\n').filter(Boolean).map((line) => {
		const at = line.indexOf(':');
		return at > 0 ? { name: line.slice(0, at), value: line.slice(at + 1).trim() } : { name: '', value: line };
	});

	const labelName = (value: AuditLabel) => t(`audit.label.${value}` as MessageKey);
	const tone = (value: AuditLabel) => (value === 'sai' ? 'bad' : value === 'khong_ro' ? 'unsure' : 'good');
	const railItems = $derived(
		(ws?.rows ?? []).map((r, i) => ({
			key: r.item_id,
			n: i + 1,
			text: r.sentence,
			done: !!r.mine,
			status: r.mine ? labelName(r.mine.label) : t('gold.status.todo'),
			label: r.mine?.label
		}))
	);

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
	{:else}
		<p class="crumb"><a href="/research/audit"><Icon name="back" size={16} />{t('audit.title')}</a></p>
		<header class="page-head">
			<div>
				<h1 class="title serif">{#if ws}{ws.name}{:else}<span class="title-ghost" style:width="min(380px, 70vw)"><Skeleton height="30px" /></span>{/if}</h1>
				<p class="facts"><span>{t('audit.blind')}</span></p>
			</div>
			<div class="row">
				<a class="btn quiet" href="/docs/huong-dan-kiem-tra-quy-pham"><Icon name="doc" size={16} />{t('audit.guide')}</a>
				{#if ws?.can_score}<a class="btn" href="/research/audit/{id}/score">{t('audit.score')}</a>{/if}
			</div>
		</header>
		{#if !ws}
			<WorkspaceSkeleton tabs={0} />
		{:else}

		<div class="ws-cols">
			<ItemRail heading={t('audit.rows')} items={railItems} {selected} onpick={pick} {done} total={ws.rows.length} progress={t('audit.mine', { done, n: ws.rows.length })}>
				{#snippet marker(item)}
					{#if item.label}
						<span class="verdict {tone(item.label)}" title={labelName(item.label)} aria-hidden="true">{ws ? ws.labels.indexOf(item.label) + 1 : ''}</span>
					{:else}
						<span class="verdict" aria-hidden="true"></span>
					{/if}
				{/snippet}
				{#snippet foot()}
					{#each others as [who, info] (who)}
						<a class="btn small" href="/research/audit/{id}/compare?other={encodeURIComponent(who)}">{t('audit.compareWith', { name: info.name })}<Icon name="arrow" size={16} /></a>
					{/each}
					{#if done}<a class="btn quiet small" href="/api/audit/sheet.csv?id={id}&source={encodeURIComponent(session.account?.username ?? '')}" download><Icon name="download" size={16} />{t('audit.downloadMine')}</a>{/if}
				{/snippet}
			</ItemRail>

			<section class="panel ws-work" aria-labelledby="item-heading">
				{#if !current}
					<p class="muted">{t('audit.pickOne')}</p>
				{:else}
					{#key current.item_id}
						<div class="ws-item" in:rise={{ y: 0, duration: DUR.press }}>
							<div class="ws-where">
								<p><strong id="item-heading">{t('audit.rowN', { n: index + 1, total: ws.rows.length })}</strong></p>
								<span class="ws-state" class:done={!!current.mine}>{current.mine ? labelName(current.mine.label) : t('gold.status.todo')}</span>
							</div>
							{#if current.context}
								<div class="block">
									<p class="label">{t('audit.context')}</p>
									<p class="context">{#each current.context.split('\n') as line, i (i)}<span>{line}</span>{/each}</p>
								</div>
							{/if}
							<div class="block">
								<p class="label">{t('audit.unit')}{#if hit}<mark class="key-mark">{t('audit.sentenceMarked')}</mark>{/if}</p>
								{#if hit}
									<p class="ws-text serif">{hit.before}<mark class="hit">{current.sentence}</mark>{hit.after}</p>
								{:else}
									<p class="ws-text serif">{current.unit_text}</p>
								{/if}
								{#if !hit && current.sentence && current.sentence !== current.unit_text.trim()}
									<p class="ws-selection small"><span class="label">{t('audit.sentence')}</span> <mark>{current.sentence}</mark></p>
								{/if}
							</div>
							<div class="block">
								<p class="label">{t('audit.norm')}</p>
								<dl class="norm">
									{#each normLines(current.norm) as line, i (i)}<dt>{line.name}</dt><dd>{line.value}</dd>{/each}
								</dl>
							</div>
						</div>
					{/key}

					<fieldset class="verdicts" disabled={busy}>
						<legend class="label">{t('audit.pick')}</legend>
						{#each ws.labels as value, i (value)}
							<label class="opt" class:on={label === value}>
								<input type="radio" name="audit-label" {value} bind:group={label} />
								<span class="key" aria-hidden="true">{i + 1}</span>
								<span><strong>{labelName(value)}</strong><span class="small muted">{t(`audit.label.${value}.d` as MessageKey)}</span></span>
							</label>
						{/each}
					</fieldset>
					<label class="field"><span>{t('audit.note')}</span><textarea rows="2" bind:value={note} placeholder={t('audit.notePh')}></textarea></label>
					<div class="row ws-actions">
						<span class="small muted">{t('audit.keys')}</span>
						<span class="spacer"></span>
						<button type="button" class="btn" disabled={busy || !label} onclick={() => save(false)}>{t('audit.save')}</button>
						<button type="button" class="btn primary" disabled={busy || !label} onclick={() => save(true)}>{t('audit.saveNext')}<Icon name="arrow" /></button>
					</div>
				{/if}
			</section>
		</div>
		{/if}
	{/if}
</div>

<style>
	.verdict {
		display: grid;
		place-items: center;
		width: 20px;
		height: 20px;
		border-radius: 5px;
		border: 1.5px solid var(--rule-strong);
		font-size: 11.5px;
		font-weight: 700;
		line-height: 1;
	}
	.verdict.good {
		border-color: var(--approve);
		background: var(--approve);
		color: var(--paper);
	}
	.verdict.bad {
		border-color: var(--reject);
		background: var(--reject);
		color: var(--paper);
	}
	.verdict.unsure {
		border-color: var(--attention);
		background: var(--attention-soft);
		color: var(--attention);
	}
	.block {
		display: grid;
		gap: 4px;
	}
	.hit,
	.key-mark {
		background: var(--hl-object);
		color: var(--ink);
		border-radius: 3px;
		-webkit-box-decoration-break: clone;
		box-decoration-break: clone;
	}
	.hit {
		padding: 0 2px;
	}
	.key-mark {
		margin-left: 8px;
		padding: 0 4px;
		font-weight: 400;
	}
	.context {
		display: grid;
		gap: 2px;
		font-size: 14px;
		color: var(--ink-2);
	}
	.norm {
		display: grid;
		grid-template-columns: minmax(110px, max-content) minmax(0, 1fr);
		gap: 6px 16px;
		margin: 2px 0 0;
		padding: 12px 16px;
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
	.verdicts {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
		gap: 8px;
		border: 0;
		padding: 0;
		margin: 0;
	}
	.verdicts legend {
		margin-bottom: 8px;
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
		transition:
			border-color var(--dur-fast) ease,
			background-color var(--dur-fast) ease;
	}
	@media (hover: hover) {
		.opt:hover {
			border-color: var(--ink-2);
		}
	}
	.opt.on {
		border-color: var(--graphite);
		background: var(--desk);
		box-shadow: inset 0 0 0 1px var(--graphite);
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
</style>
