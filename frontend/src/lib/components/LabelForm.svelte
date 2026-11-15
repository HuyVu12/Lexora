<script lang="ts">
	import { tick } from 'svelte';
	import Icon from './Icon.svelte';
	import Term from './Term.svelte';
	import { api } from '#lib/api.js';
	import { t } from '#lib/i18n/index.svelte.js';
	import type { LabelFields, QuestionType, ExpectedStatus, UnitCandidate, UnitRef } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	// One annotation: question type, expected behaviour, relevant units (searched by BM25 over the frozen corpus) and a note.
	let {
		setId,
		fields = $bindable(),
		note = $bindable(),
		seed = '',
		name = 'label'
	}: { setId: string; fields: LabelFields; note: string; seed?: string; name?: string } = $props();

	const TYPES: QuestionType[] = ['lookup', 'synthesis', 'temporal', 'out_of_scope'];
	const STATUSES: ExpectedStatus[] = ['answer', 'refuse'];
	// Every unit seen so far (search results, their parents, chosen units loaded from a saved label), by ID.
	let known = $state<Record<string, UnitRef>>({});
	let query = $state('');
	let found = $state<UnitCandidate[]>([]);
	let searching = $state(false);

	// Show the document, path and text of every chosen unit; fetch the ones not seen yet.
	$effect(() => {
		const missing = fields.relevant_unit_ids.filter((id) => !(id in known));
		if (!missing.length) return;
		api<{ units: UnitRef[] }>(`/api/question-set/units?set_id=${encodeURIComponent(setId)}&ids=${encodeURIComponent(missing.join(','))}`)
			.then((r) => {
				for (const u of r.units) known[u.unit_id] = u;
			})
			.catch(() => undefined);
	});

	// Start each question with candidates for its own wording.
	$effect(() => {
		query = seed;
	});

	let ticket = 0;
	$effect(() => {
		const q = query.trim();
		if (q.length < 2) {
			found = [];
			return;
		}
		const mine = ++ticket;
		const timer = setTimeout(async () => {
			searching = true;
			try {
				const r = await api<{ candidates: UnitCandidate[] }>(`/api/question-set/candidates?k=8&set_id=${encodeURIComponent(setId)}&q=${encodeURIComponent(q)}`);
				if (mine === ticket) {
					found = r.candidates;
					for (const c of r.candidates) for (const u of [...c.parents, c]) known[u.unit_id] ??= u;
				}
			} finally {
				if (mine === ticket) searching = false;
			}
		}, 250);
		return () => clearTimeout(timer);
	});

	// Results as a tree: each parent Clause once, with every leaf found under it grouped below it, so a rule that sits
	// in a Clause's lead sentence ("trong thời hạn 14 ngày ..., trừ trường hợp sau đây") can be chosen, not only its
	// Points, and an indented row always sits under its real parent. Top-level groups keep the rank of their best
	// member; the rows under one parent follow the statute (a, b, c, d).
	type Row = UnitRef & { depth: number; parent: boolean };
	const rows = $derived.by(() => {
		const children = new Map<string, Row[]>();
		const seen = new Set<string>();
		for (const c of found) {
			const chain: UnitRef[] = [...c.parents, c];
			chain.forEach((u, depth) => {
				if (seen.has(u.unit_id)) return;
				seen.add(u.unit_id);
				const under = depth ? chain[depth - 1].unit_id : '';
				const row = { unit_id: u.unit_id, document: u.document, document_title: u.document_title, path: u.path, text: u.text, order: u.order, depth, parent: depth < c.parents.length };
				children.set(under, [...(children.get(under) ?? []), row]);
			});
		}
		const out: Row[] = [];
		const walk = (id: string) => {
			const level = children.get(id) ?? [];
			for (const row of id ? [...level].sort((a, b) => a.order - b.order) : level) {
				out.push(row);
				walk(row.unit_id);
			}
		};
		walk('');
		return out;
	});

	const short = (id: string) => id.split('/').slice(1).join('/') || id;
	const spoken = (id: string) => (known[id] ? `${known[id].document}, ${known[id].path}` : short(id));

	// Keep keyboard focus in place: choosing a unit focuses its "chosen" mark in the same row; removing one focuses the
	// next remove button (or the previous one, or the search box when the list is empty).
	let foundList = $state<HTMLUListElement>();
	let chosenList = $state<HTMLUListElement>();
	let searchBox = $state<HTMLInputElement>();
	const add = async (id: string) => {
		if (!fields.relevant_unit_ids.includes(id)) fields.relevant_unit_ids = [...fields.relevant_unit_ids, id];
		await tick();
		foundList?.querySelector<HTMLElement>(`li[data-unit="${CSS.escape(id)}"] .picked-mark`)?.focus();
	};
	const drop = async (id: string) => {
		const at = fields.relevant_unit_ids.indexOf(id);
		fields.relevant_unit_ids = fields.relevant_unit_ids.filter((u) => u !== id);
		await tick();
		const buttons = chosenList?.querySelectorAll<HTMLButtonElement>('button') ?? [];
		(buttons[Math.min(at, buttons.length - 1)] ?? searchBox)?.focus();
	};
</script>

{#snippet where(u: UnitRef | undefined, id: string)}
	<span class="small where" title={id}>{#if u}<span class="doc" title={u.document_title}>{u.document}</span><span class="sep" aria-hidden="true">·</span><span class="muted">{u.path}</span>{:else}<span class="muted">{short(id)}</span>{/if}</span>
{/snippet}

<div class="label-form">
	<fieldset>
		<legend class="label">{t('qs.field.type')}</legend>
		<div class="options">
			{#each TYPES as kind (kind)}
				<label class="option"><input type="radio" name="{name}-type" value={kind} bind:group={fields.question_type} /><strong><Term key={`q_${kind}`} focusable={false}>{t(`qs.type.${kind}` as MessageKey)}</Term></strong><span>{t(`qs.type.${kind}.hint` as MessageKey)}</span></label>
			{/each}
		</div>
	</fieldset>

	<fieldset>
		<legend class="label">{t('qs.field.status')}</legend>
		<div class="options two">
			{#each STATUSES as status (status)}
				<label class="option"><input type="radio" name="{name}-status" value={status} bind:group={fields.expected_status} /><strong><Term key={`expect_${status}`} focusable={false}>{t(`qs.status.${status}` as MessageKey)}</Term></strong><span>{t(`qs.status.${status}.hint` as MessageKey)}</span></label>
			{/each}
		</div>
	</fieldset>

	<fieldset>
		<legend class="label"><Term key="relevant_units">{t('qs.field.units', { n: fields.relevant_unit_ids.length })}</Term></legend>
		{#if fields.relevant_unit_ids.length}
			<ul class="chosen" bind:this={chosenList}>
				{#each fields.relevant_unit_ids as id (id)}
					<li>
						<div>{@render where(known[id], id)}<span class="serif">{known[id]?.text.trim() ?? '…'}</span></div>
						<button type="button" class="btn quiet small" onclick={() => drop(id)} aria-label={t('qs.unit.remove', { id: spoken(id) })}><Icon name="x" size={16} /></button>
					</li>
				{/each}
			</ul>
		{:else}
			<p class="small muted">{fields.expected_status === 'refuse' ? t('qs.units.noneRefuse') : t('qs.units.none')}</p>
		{/if}
		<label class="field search">
			<span>{t('qs.unit.search')}</span>
			<input type="search" bind:this={searchBox} bind:value={query} placeholder={t('qs.unit.searchPh')} autocomplete="off" />
		</label>
		{#if searching}<p class="small muted">{t('common.loading')}</p>{/if}
		{#if found.length}
			<ul class="found" bind:this={foundList}>
				{#each rows as c (c.unit_id)}
					<li class:picked={fields.relevant_unit_ids.includes(c.unit_id)} class:parent={c.parent} style:--depth={Math.min(c.depth, 3)} data-unit={c.unit_id}>
						<div>{@render where(c, c.unit_id)}<span class="serif">{c.text.trim()}</span></div>
						{#if fields.relevant_unit_ids.includes(c.unit_id)}
							<span class="small picked-mark" tabindex="-1"><Icon name="check" size={16} />{t('qs.unit.added')}</span>
						{:else}
							<button type="button" class="btn small" onclick={() => add(c.unit_id)}><Icon name="plus" size={16} />{t('qs.unit.add')}</button>
						{/if}
					</li>
				{/each}
			</ul>
		{/if}
	</fieldset>

	<label class="field"><span>{t('qs.field.note')} <span class="hint">({t('common.optional')})</span></span><textarea rows="2" maxlength="2000" bind:value={note}></textarea></label>
</div>

<style>
	.label-form {
		display: grid;
		gap: 18px;
	}
	fieldset {
		margin: 0;
		padding: 0;
		border: 0;
		display: grid;
		gap: 8px;
		min-width: 0;
	}
	legend {
		padding: 0;
		margin-bottom: 6px;
	}
	.options {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 8px;
	}
	.option {
		display: grid;
		grid-template-columns: auto 1fr;
		column-gap: 8px;
		align-items: start;
		padding: 9px 11px;
		border: 1px solid var(--rule);
		border-radius: var(--r-control);
		background: var(--paper);
		cursor: pointer;
	}
	.option:hover {
		border-color: var(--rule-strong);
	}
	.option:has(input:checked) {
		border-color: var(--graphite);
		box-shadow: inset 0 0 0 1px var(--graphite);
	}
	.option input {
		margin-top: 3px;
		grid-row: span 2;
	}
	.option span {
		font-size: 13px;
		color: var(--muted);
	}
	.chosen,
	.found {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 6px;
	}
	.chosen li,
	.found li {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 10px;
		padding: 8px 10px;
		border-radius: var(--r-control);
	}
	.chosen li {
		background: var(--hl-actor);
		background: color-mix(in srgb, var(--hl-actor) 45%, var(--paper));
	}
	.found li {
		border: 1px solid var(--rule);
		margin-inline-start: calc(var(--depth, 0) * 20px);
	}
	.found li.parent {
		background: color-mix(in srgb, var(--desk) 40%, var(--paper));
	}
	.found li.picked {
		border-color: #b9dcc5;
		background: var(--approve-soft);
	}
	.chosen li > div,
	.found li > div {
		display: grid;
		gap: 2px;
		min-width: 0;
	}
	.where {
		display: flex;
		flex-wrap: wrap;
		column-gap: 6px;
	}
	.where .doc {
		color: var(--ink-2);
		font-weight: 600;
	}
	.where .sep {
		color: var(--muted);
	}
	.serif {
		font-size: 15px;
		line-height: 1.5;
		white-space: pre-line;
	}
	.picked-mark {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		color: var(--approve);
		white-space: nowrap;
	}
	.search {
		margin-top: 6px;
	}
	@media (max-width: 700px) {
		.options {
			grid-template-columns: 1fr;
		}
		/* Narrow screens: a smaller indent step, and the action under the text so nested rows keep a readable measure. */
		.found li {
			flex-wrap: wrap;
			margin-inline-start: calc(var(--depth, 0) * 12px);
		}
		.found li > div {
			flex: 1 1 100%;
		}
		.found li > :last-child {
			margin-inline-start: auto;
		}
		/* Document and path usually wrap onto two lines here; a separator would dangle at the line end. */
		.where .sep {
			display: none;
		}
	}
</style>
