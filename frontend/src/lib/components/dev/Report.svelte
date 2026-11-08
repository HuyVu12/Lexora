<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import Term from '#lib/components/Term.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDate } from '#lib/i18n/index.svelte.js';
	import { act, notify } from '#lib/toast.svelte.js';
	import type { DevReport, NoteKey } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	let { data, reload }: { data: DevReport; reload: () => void } = $props();

	const NOTES: NoteKey[] = ['limitations', 'next_steps', 'questions'];
	const CATEGORIES = ['context', 'not_found', 'modality_only', 'other'];
	const COLORS: Record<string, string> = { context: '#6f9bc4', not_found: 'var(--reject)', modality_only: '#d9a43a', other: 'var(--muted)' };
	const pct = (v: number | null) => (v === null ? '-' : `${(v * 100).toFixed(1)}%`);
	const top = $derived(Math.max(0.01, ...data.extraction.map((r) => r.rejected_rate ?? 0)));
	let editing = $state(false);
	let drafts = $state<Record<NoteKey, string>>({ limitations: '', next_steps: '', questions: '' });
	let saving = $state(false);

	function edit() {
		drafts = { limitations: data.notes.limitations.join('\n'), next_steps: data.notes.next_steps.join('\n'), questions: data.notes.questions.join('\n') };
		editing = true;
	}
	async function save() {
		saving = true;
		const notes = Object.fromEntries(NOTES.map((k) => [k, drafts[k].split('\n').map((l) => l.trim()).filter(Boolean)]));
		const ok = await act(() => api('/api/dev/notes', { notes }));
		saving = false;
		if (ok) {
			editing = false;
			notify({ key: 'dev.report.saved' });
			reload();
		}
	}
</script>

<section class="panel head" aria-labelledby="report-heading">
	<div>
		<h2 class="heading" id="report-heading">{t('dev.report.title')}</h2>
		<p class="small muted">{t('dev.report.lead', { at: formatDate(data.generated_at) })}</p>
	</div>
	<a class="btn primary" href="/api/dev/report.html" download><Icon name="download" size={16} />{t('dev.report.export')}</a>
</section>

<section class="panel" aria-labelledby="rq-heading">
	<h2 class="heading" id="rq-heading">{t('dev.report.status')}</h2>
	<div class="table-scroll">
		<table class="table">
			<thead><tr><th scope="col">{t('dev.report.rq')}</th><th scope="col">{t('dev.report.state')}</th><th scope="col">{t('dev.report.facts')}</th></tr></thead>
			<tbody>
				{#each data.status as s (s.rq)}
					<tr>
						<th scope="row"><strong>{s.rq}</strong> {s.title}</th>
						<td><span class="chip state-{s.state}">{t(`dev.report.state.${s.state}` as MessageKey)}</span></td>
						<td>{s.facts}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</section>

<section class="panel" aria-labelledby="models-heading">
	<h2 class="heading" id="models-heading">{t('dev.report.models')}</h2>
	{#if data.extraction.length}
		<div class="table-scroll">
			<table class="table">
				<thead>
					<tr>
						<th scope="col">{t('dev.col.model')}</th>
						<th scope="col" class="num">{t('dev.report.batches')}</th>
						<th scope="col" class="num">{t('results.col.answered')}</th>
						<th scope="col" class="num"><Term key="dk3">ĐK3</Term></th>
						<th scope="col" class="num"><Term key="dk4">ĐK4</Term></th>
						<th scope="col" class="num"><Term key="rejected_claims">{t('results.col.rejected')}</Term></th>
						<th scope="col" class="num"><Term key="planted_errors">{t('results.col.injection')}</Term></th>
						<th scope="col" class="num">{t('results.col.callErrors')}</th>
					</tr>
				</thead>
				<tbody>
					{#each data.extraction as r (r.model)}
						<tr>
							<th scope="row"><code>{r.model}</code></th>
							<td class="num">{r.batches_ok}/{r.batches_planned ?? '-'}</td>
							<td class="num">{pct(r.sentence_answer_rate)}</td>
							<td class="num">{r.dk3}</td>
							<td class="num">{r.dk4}</td>
							<td class="num">{pct(r.rejected_rate)}</td>
							<td class="num">{pct(r.detectable_rate)}</td>
							<td class="num">{pct(r.call_error_rate)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		{#if data.sampled_models.length}<p class="small muted">{t('dev.report.sampled', { models: data.sampled_models.join(', ') })}</p>{/if}

		<h3 class="label">{t('results.explained')}</h3>
		<div class="legend">{#each CATEGORIES as c (c)}<span><i style="background:{COLORS[c]}"></i>{t(`results.explained.${c}` as MessageKey)}</span>{/each}</div>
		<div class="bars" role="img" aria-label={data.extraction.map((r) => `${r.model} ${pct(r.rejected_rate)}`).join(', ')}>
			{#each data.extraction as r (r.model)}
				<div class="bar-row">
					<code class="name">{r.model}</code>
					<span class="track"><span class="bar" style="width:{((r.rejected_rate ?? 0) / top) * 100}%">
						{#each CATEGORIES as c (c)}{#if r.explained[c]}<span style="flex:{r.explained[c]};background:{COLORS[c]}" title="{t(`results.explained.${c}` as MessageKey)}: {r.explained[c]}"></span>{/if}{/each}
					</span></span>
					<strong class="num pct">{pct(r.rejected_rate)}</strong>
				</div>
			{/each}
		</div>
		<p class="small muted">{t('results.explained.note')}</p>
	{:else}
		<p class="small muted">{t('dev.report.noRuns')}</p>
	{/if}
</section>

<section class="panel" aria-labelledby="notes-heading">
	<div class="notes-head">
		<h2 class="heading" id="notes-heading">{t('dev.report.notes')}</h2>
		{#if data.can_change && !editing}<button type="button" class="btn small" onclick={edit}><Icon name="edit" size={16} />{t('dev.report.edit')}</button>{/if}
	</div>
	<p class="small muted">{data.can_change ? t('dev.report.notesLead') : t('dev.report.notesReadOnly')}</p>
	{#if editing}
		<form class="notes" onsubmit={(e) => { e.preventDefault(); save(); }}>
			{#each NOTES as k (k)}
				<div class="field">
					<label for="note-{k}">{t(`dev.report.note.${k}` as MessageKey)}</label>
					<textarea id="note-{k}" rows="7" bind:value={drafts[k]}></textarea>
				</div>
			{/each}
			<div class="row actions">
				<button type="submit" class="btn primary" disabled={saving}>{t('dev.save')}</button>
				<button type="button" class="btn quiet" onclick={() => (editing = false)}>{t('dev.cancel')}</button>
			</div>
		</form>
	{:else}
		<div class="notes">
			{#each NOTES as k (k)}
				<div><h3 class="label">{t(`dev.report.note.${k}` as MessageKey)}</h3><ul>{#each data.notes[k] as line, i (i)}<li>{line}</li>{/each}</ul></div>
			{/each}
		</div>
	{/if}
</section>

<style>
	.panel.head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		flex-wrap: wrap;
		gap: 12px;
	}
	.state-done {
		color: var(--approve);
		border-color: currentColor;
	}
	.state-partial {
		color: var(--attention);
		border-color: currentColor;
	}
	.state-todo {
		color: var(--muted);
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 4px 16px;
		font-size: 13px;
		color: var(--ink-2);
	}
	.legend i {
		display: inline-block;
		width: 10px;
		height: 10px;
		border-radius: 2px;
		margin-right: 6px;
	}
	.bars {
		display: grid;
		gap: 8px;
		font-size: 13.5px;
	}
	.bar-row {
		display: grid;
		grid-template-columns: 15rem minmax(0, 1fr) 4.5rem;
		grid-template-areas: 'name track pct';
		gap: 4px 12px;
		align-items: center;
	}
	.name {
		grid-area: name;
		overflow-wrap: anywhere;
	}
	.track {
		grid-area: track;
		height: 16px;
		border-left: 1px solid var(--rule-strong);
	}
	.pct {
		grid-area: pct;
		text-align: right;
	}
	.bar {
		display: flex;
		height: 100%;
		min-width: 1px;
	}
	.bar span {
		height: 100%;
	}
	.notes-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 12px;
	}
	.notes {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 16px;
	}
	.notes ul {
		margin: 6px 0 0;
		padding-left: 18px;
		display: grid;
		gap: 6px;
		font-size: 14px;
	}
	.actions {
		grid-column: 1 / -1;
	}
	@media (max-width: 860px) {
		.notes {
			grid-template-columns: 1fr;
		}
		.bar-row {
			grid-template-columns: minmax(0, 1fr) 4rem;
			grid-template-areas: 'name pct' 'track track';
		}
	}
</style>
