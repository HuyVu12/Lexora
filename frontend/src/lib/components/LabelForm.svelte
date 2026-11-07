<script lang="ts">
	import Icon from './Icon.svelte';
	import { api } from '#lib/api.js';
	import { t } from '#lib/i18n/index.svelte.js';
	import type { LabelFields, QuestionType, ExpectedStatus, UnitCandidate } from '#lib/types.js';
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
	let texts = $state<Record<string, string>>({});
	let query = $state('');
	let found = $state<UnitCandidate[]>([]);
	let searching = $state(false);

	// Show the text of every chosen unit; fetch the ones not seen yet.
	$effect(() => {
		const missing = fields.relevant_unit_ids.filter((id) => !(id in texts));
		if (!missing.length) return;
		api<{ units: { unit_id: string; text: string }[] }>(`/api/question-set/units?set_id=${encodeURIComponent(setId)}&ids=${encodeURIComponent(missing.join(','))}`)
			.then((r) => {
				for (const u of r.units) texts[u.unit_id] = u.text;
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
					for (const c of r.candidates) texts[c.unit_id] ??= c.text;
				}
			} finally {
				if (mine === ticket) searching = false;
			}
		}, 250);
		return () => clearTimeout(timer);
	});

	const short = (id: string) => id.split('/').slice(1).join('/') || id;
	const add = (id: string) => {
		if (!fields.relevant_unit_ids.includes(id)) fields.relevant_unit_ids = [...fields.relevant_unit_ids, id];
	};
	const drop = (id: string) => (fields.relevant_unit_ids = fields.relevant_unit_ids.filter((u) => u !== id));
</script>

<div class="label-form">
	<fieldset>
		<legend class="label">{t('qs.field.type')}</legend>
		<div class="options">
			{#each TYPES as kind (kind)}
				<label class="option"><input type="radio" name="{name}-type" value={kind} bind:group={fields.question_type} /><strong>{t(`qs.type.${kind}` as MessageKey)}</strong><span>{t(`qs.type.${kind}.hint` as MessageKey)}</span></label>
			{/each}
		</div>
	</fieldset>

	<fieldset>
		<legend class="label">{t('qs.field.status')}</legend>
		<div class="options two">
			{#each STATUSES as status (status)}
				<label class="option"><input type="radio" name="{name}-status" value={status} bind:group={fields.expected_status} /><strong>{t(`qs.status.${status}` as MessageKey)}</strong><span>{t(`qs.status.${status}.hint` as MessageKey)}</span></label>
			{/each}
		</div>
	</fieldset>

	<fieldset>
		<legend class="label">{t('qs.field.units', { n: fields.relevant_unit_ids.length })}</legend>
		{#if fields.relevant_unit_ids.length}
			<ul class="chosen">
				{#each fields.relevant_unit_ids as id (id)}
					<li>
						<div><code>{short(id)}</code><span class="serif">{texts[id]?.trim() ?? '…'}</span></div>
						<button type="button" class="btn quiet small" onclick={() => drop(id)} aria-label={t('qs.unit.remove', { id: short(id) })}><Icon name="x" size={16} /></button>
					</li>
				{/each}
			</ul>
		{:else}
			<p class="small muted">{fields.expected_status === 'refuse' ? t('qs.units.noneRefuse') : t('qs.units.none')}</p>
		{/if}
		<label class="field search">
			<span>{t('qs.unit.search')}</span>
			<input type="search" bind:value={query} placeholder={t('qs.unit.searchPh')} autocomplete="off" />
		</label>
		{#if searching}<p class="small muted">{t('common.loading')}</p>{/if}
		{#if found.length}
			<ul class="found">
				{#each found as c (c.unit_id)}
					<li class:picked={fields.relevant_unit_ids.includes(c.unit_id)}>
						<div><span class="small muted">{c.path}</span><span class="serif">{c.text.trim()}</span></div>
						{#if fields.relevant_unit_ids.includes(c.unit_id)}
							<span class="small picked-mark"><Icon name="check" size={16} />{t('qs.unit.added')}</span>
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
	.chosen code {
		font-size: 12px;
		color: var(--ink-2);
	}
	.serif {
		font-size: 15px;
		line-height: 1.5;
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
	}
</style>
