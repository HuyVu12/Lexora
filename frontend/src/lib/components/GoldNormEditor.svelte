<script lang="ts">
	import Icon from './Icon.svelte';
	import Term from './Term.svelte';
	import { t } from '#lib/i18n/index.svelte.js';
	import type { GoldModality, GoldNorm } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	// Norms of one sentence. Every text field is a verbatim phrase; "Fill" copies the phrase selected in the sentence.
	let {
		norms = $bindable(),
		slots,
		modalities,
		selection = '',
		disabled = false
	}: { norms: GoldNorm[]; slots: string[]; modalities: GoldModality[]; selection?: string; disabled?: boolean } = $props();

	const modalityKey = (m: GoldModality) => (m === 'unknown' ? 'modality.unknown' : `modality.${m}`) as MessageKey;

	function add() {
		norms = [...norms, { modality: 'obligation', modality_cue: null, slots: {} }];
	}
	function remove(index: number) {
		norms = norms.filter((_, i) => i !== index);
	}
	function fill(index: number, slot: string) {
		if (!selection) return;
		norms[index].slots = { ...norms[index].slots, [slot]: selection };
	}
	function fillCue(index: number) {
		if (selection) norms[index].modality_cue = selection;
	}
</script>

<div class="norms">
	{#each norms as norm, i (i)}
		<fieldset class="norm" {disabled}>
			<legend>{t('gold.norm', { n: i + 1 })}</legend>
			<button type="button" class="btn quiet small remove" onclick={() => remove(i)}><Icon name="x" size={16} />{t('gold.removeNorm')}</button>
			<div class="head">
				<label class="field"
					><span><Term key="modality" /></span>
					<select bind:value={norm.modality}>
						{#each modalities as m (m)}<option value={m}>{t(modalityKey(m))}</option>{/each}
					</select>
				</label>
				<div class="field">
					<label for="cue-{i}"><Term key="cue">{t('gold.cue')}</Term></label>
					<div class="fill-row">
						<input id="cue-{i}" value={norm.modality_cue ?? ''} oninput={(e) => (norm.modality_cue = e.currentTarget.value || null)} />
						<button type="button" class="btn small" disabled={!selection} aria-label={t('gold.fillLabel', { slot: t('gold.cue') })} onclick={() => fillCue(i)}>{t('gold.fill')}</button>
					</div>
					<span class="hint">{t('gold.cueHint')}</span>
				</div>
			</div>
			<div class="slots">
				{#each slots as slot (slot)}
					<div class="field">
						<label for="slot-{i}-{slot}"><Term key={slot}>{t(`slot.${slot}` as MessageKey)}</Term></label>
						<div class="fill-row">
							<input
								id="slot-{i}-{slot}"
								value={norm.slots[slot] ?? ''}
								oninput={(e) => (norm.slots = { ...norm.slots, [slot]: e.currentTarget.value })}
							/>
							<button type="button" class="btn small" disabled={!selection} aria-label={t('gold.fillLabel', { slot: t(`slot.${slot}` as MessageKey) })} onclick={() => fill(i, slot)}
								>{t('gold.fill')}</button
							>
						</div>
					</div>
				{/each}
			</div>
		</fieldset>
	{/each}
	<div><button type="button" class="btn" {disabled} onclick={add}><Icon name="plus" />{t('gold.addNorm')}</button></div>
</div>

<style>
	.norms {
		display: grid;
		gap: 14px;
	}
	.norm {
		position: relative;
		display: grid;
		gap: 12px;
		margin: 0;
		padding: 14px 16px 16px;
		border: 1px solid var(--rule);
		border-radius: var(--r-panel);
	}
	legend {
		padding: 0 6px;
		font-weight: 600;
	}
	.remove {
		position: absolute;
		top: 6px;
		right: 8px;
	}
	.head {
		display: grid;
		grid-template-columns: minmax(160px, 0.8fr) minmax(0, 1.2fr);
		gap: 12px;
		align-items: start;
	}
	.field > label {
		font-size: 14px;
		font-weight: 500;
	}
	.fill-row .btn {
		min-height: 40px;
	}
	.slots {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 10px 14px;
	}
	.fill-row {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 6px;
	}
	@media (max-width: 760px) {
		.head,
		.slots {
			grid-template-columns: 1fr;
		}
	}
</style>
