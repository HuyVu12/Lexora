<script lang="ts">
	import Icon from './Icon.svelte';
	import Term from './Term.svelte';
	import type { Claim, Unit } from '#lib/types.js';
	import { ROLE_CLASS, SLOT_ORDER, MODALITIES, slotKey, modalityKey, modalityTerm } from '#lib/roles.js';
	import { t } from '#lib/i18n/index.svelte.js';
	import { selectionAnchor, SelectionError } from '#lib/selection.js';
	import { notify } from '#lib/toast.svelte.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	let {
		claim,
		number,
		units,
		review
	}: {
		claim: Claim;
		number: number;
		units: Map<string, Unit>;
		review: (itemId: string | null, decision: string, payload?: Record<string, unknown>) => Promise<unknown>;
	} = $props();

	let editing = $state(false);
	let field = $state<string>('object');
	let newModality = $state<string>('obligation');
	let note = $state('');
	let busy = $state(false);

	$effect(() => {
		// A different norm opens with a closed editor and its own note.
		void claim.id;
		editing = false;
		note = claim.reviewer_note ?? '';
	});

	const rows = $derived(
		SLOT_ORDER.filter((name) => claim.slots[name]?.state === 'present' || name === 'actor' || name === 'action').map((name) => ({
			name,
			slot: claim.slots[name]
		}))
	);
	const title = $derived.by(() => {
		const part = (name: string) => (claim.slots[name]?.state === 'present' ? claim.slots[name].text ?? '' : '');
		const action = part('action');
		const object = part('object');
		return [part('actor'), action, object && !action.includes(object) ? object : ''].filter(Boolean).join(' ') || claim.quote?.quote || claim.label;
	});

	async function run(fn: () => Promise<unknown>) {
		busy = true;
		try {
			await fn();
		} catch (e) {
			notify(e instanceof SelectionError ? t(e.key) : e instanceof Error ? e.message : String(e), true);
		} finally {
			busy = false;
		}
	}

	const decide = (value: 'approve' | 'reject') => run(() => review(claim.id, claim.decision === value ? 'clear' : value));
	const useSelection = () =>
		run(async () => {
			const anchor = selectionAnchor(units);
			await review(claim.id, 'edit', field === 'modality' ? { field: 'modality', modality: newModality, ...anchor } : { field: 'slot', slot: field, state: 'present', ...anchor });
			getSelection()?.removeAllRanges();
			notify({ key: 'review.updated' });
		});
	const setState = (state: 'not_present' | 'unknown') =>
		run(() => review(claim.id, 'edit', field === 'modality' ? { field: 'modality', modality: 'unknown' } : { field: 'slot', slot: field, state }));
</script>

<article class="card sheet" aria-labelledby="norm-title">
	<header>
		<span class="num {claim.decision ?? 'pending'}" aria-hidden="true">{number}</span>
		<h2 id="norm-title" class="heading">{title}</h2>
	</header>
	<div class="meta">
		<span class="chip dark"><Term key={modalityTerm(claim.modality)}>{t(modalityKey(claim.modality))}</Term></span>
		{#if claim.origin === 'ai' || claim.origin === 'manual' || claim.origin === 'cue'}
			<span class="chip"><Term key={claim.origin}>{t(`origin.${claim.origin}` as MessageKey)}</Term></span>
		{/if}
		{#if claim.edited}<span class="chip">{t('review.edited', { n: claim.edits.length })}</span>{/if}
		{#if claim.decision_mode === 'batch'}<span class="small muted">{t('review.batchMode')}</span>{/if}
	</div>

	<dl class="slots">
		{#each rows as { name, slot } (name)}
			<dt><span class="swatch {ROLE_CLASS[name]}" aria-hidden="true"></span><Term key={name}>{t(slotKey(name))}</Term></dt>
			<dd class:unknown={slot?.state !== 'present'}>
				{slot?.state === 'present' ? slot.text : slot?.state === 'not_present' ? t('review.notPresent') : t('review.unknown')}
			</dd>
		{/each}
	</dl>

	{#each claim.reasons as reason (reason)}
		<p class="attention"><Icon name="warn" size={16} /><span><Term key="attention" focusable={false}>{reason}</Term></span></p>
	{/each}
	{#if claim.origin === 'manual' && (claim.slots.actor?.state !== 'present' || claim.slots.action?.state !== 'present')}
		<p class="pencil">{t('review.manualHint')}</p>
	{/if}
	{#if claim.ai_note}<p class="pencil">{claim.ai_note}</p>{/if}
	{#if claim.reviewer_note && !editing}<p class="pencil">“{claim.reviewer_note}”</p>{/if}

	<div class="actions">
		<button type="button" class="btn decide-approve {claim.decision === 'approve' ? 'decided' : 'primary'}" aria-pressed={claim.decision === 'approve'} disabled={busy} onclick={() => decide('approve')}>
			<Icon name="check" />{claim.decision === 'approve' ? t('review.approved') : t('review.approve')}
		</button>
		<button type="button" class="btn decide-reject {claim.decision === 'reject' ? 'decided' : 'quiet'}" aria-pressed={claim.decision === 'reject'} disabled={busy} onclick={() => decide('reject')}>
			<Icon name="x" />{claim.decision === 'reject' ? t('review.rejected') : t('review.reject')}
		</button>
		<button type="button" class="btn quiet" aria-expanded={editing} onclick={() => (editing = !editing)}>
			<Icon name="edit" />{editing ? t('review.editing') : t('review.edit')}
		</button>
	</div>

	{#if editing}
		<div class="editor">
			<label class="field">
				<span>{t('review.editField')}</span>
				<select bind:value={field}>
					{#each SLOT_ORDER as name (name)}<option value={name}>{t(slotKey(name))}</option>{/each}
					<option value="modality">{t('review.modalityField')}</option>
				</select>
			</label>
			{#if field === 'modality'}
				<label class="field">
					<span>{t('review.newModality')}</span>
					<select bind:value={newModality}>
						{#each MODALITIES as m (m)}<option value={m}>{t(modalityKey(m))}</option>{/each}
					</select>
				</label>
			{/if}
			<p class="small muted">{field === 'modality' ? t('review.selectModalityHint') : t('review.selectHint')}</p>
			<div class="row">
				<button type="button" class="btn primary small" disabled={busy} onmousedown={(e) => e.preventDefault()} onclick={useSelection}>{t('review.useSelection')}</button>
				{#if field === 'modality'}
					<button type="button" class="btn small" disabled={busy} onclick={() => setState('unknown')}>{t('modality.unknown')}</button>
				{:else}
					<button type="button" class="btn small" disabled={busy} onclick={() => setState('not_present')}>{t('review.notPresent')}</button>
					<button type="button" class="btn small" disabled={busy} onclick={() => setState('unknown')}>{t('review.unknown')}</button>
				{/if}
			</div>
			<label class="field">
				<span>{t('review.note')}</span>
				<textarea rows="2" maxlength="1000" placeholder={t('review.notePh')} bind:value={note}></textarea>
			</label>
			<div class="row">
				<button type="button" class="btn small" disabled={busy} onclick={() => run(() => review(claim.id, 'edit', { field: 'note', text: note }))}>{t('review.saveNote')}</button>
				{#if claim.edited}
					<button type="button" class="btn quiet small" disabled={busy} onclick={() => run(() => review(claim.id, 'edit', { field: 'restore' }))}>{t('review.restore')}</button>
				{/if}
				<button type="button" class="btn quiet small" onclick={() => (editing = false)}>{t('review.closeEditor')}</button>
				{#if claim.origin === 'manual'}
					<button type="button" class="btn quiet small danger" disabled={busy} onclick={() => run(async () => { await review(claim.id, 'remove_claim'); notify({ key: 'review.removed' }); })}>{t('review.remove')}</button>
				{/if}
			</div>
		</div>
	{/if}
</article>

<style>
	.card {
		padding: 20px 22px;
		display: grid;
		gap: 14px;
	}
	header {
		display: flex;
		gap: 12px;
		align-items: flex-start;
	}
	.num {
		flex: none;
		min-width: 30px;
		height: 24px;
		padding: 0 7px;
		border-radius: 0 4px 4px 0;
		color: #fff;
		font-weight: 600;
		font-size: 13px;
		display: grid;
		place-items: center;
		margin-top: 1px;
	}
	.num.pending {
		background: var(--flag);
	}
	.num.approve {
		background: var(--approve);
	}
	.num.reject {
		background: var(--reject);
	}
	.meta {
		display: flex;
		gap: 6px 8px;
		flex-wrap: wrap;
		align-items: center;
	}
	.meta .chip.dark :global(.term) {
		text-decoration-color: rgb(255 255 255 / 0.6);
	}
	.slots {
		display: grid;
		grid-template-columns: 132px minmax(0, 1fr);
		gap: 8px 12px;
		margin: 0;
		font-size: 14.5px;
	}
	.slots dt {
		display: flex;
		align-items: center;
		gap: 8px;
		color: var(--ink-2);
	}
	.slots dd {
		margin: 0;
		overflow-wrap: anywhere;
	}
	.slots dd.unknown {
		color: var(--muted);
		font-style: italic;
	}
	.attention {
		display: flex;
		gap: 8px;
		align-items: flex-start;
		font-size: 14px;
		color: var(--attention);
	}
	.actions {
		display: flex;
		gap: 6px;
		flex-wrap: wrap;
	}
	.actions .btn {
		padding-inline: 12px;
	}
	.danger {
		color: var(--reject);
		margin-left: auto;
	}
	/* Graphite controls; green and red only mark a decision already taken. */
	.decided {
		font-weight: 600;
	}
	.decide-approve.decided {
		background: var(--approve-soft);
		border-color: color-mix(in srgb, var(--approve) 45%, white);
		color: var(--approve);
	}
	.decide-reject.decided {
		background: var(--reject-soft);
		border-color: color-mix(in srgb, var(--reject) 45%, white);
		color: var(--reject);
	}
	.editor {
		display: grid;
		gap: 12px;
		padding-top: 14px;
		border-top: 1px dashed var(--rule-strong);
	}
</style>
