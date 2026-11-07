<script lang="ts" module>
	export type Focus = { kind: 'claim' | 'gap'; id: string } | null;
</script>

<script lang="ts">
	import type { Article, Claim, Gap, Unit } from '#lib/types.js';
	import { ROLE_CLASS } from '#lib/roles.js';
	import { t } from '#lib/i18n/index.svelte.js';

	// The statute sheet: every extracted part is a highlighter stroke on its exact characters,
	// the modality cue is circled in pencil, each norm is a paper flag in the margin.
	let {
		article,
		claims,
		gaps,
		numbers,
		focus,
		onfocus,
		provenance = ''
	}: {
		article: Article;
		claims: Claim[];
		gaps: Gap[];
		numbers: Map<string, number>;
		focus: Focus;
		onfocus: (focus: Focus) => void;
		provenance?: string;
	} = $props();

	type Mark = { start: number; end: number; cls: string; claim?: Claim; gap?: Gap; cue?: boolean };
	type Piece = { text: string; marks: Mark[] };

	function marksFor(unit: Unit): Mark[] {
		const marks: Mark[] = [];
		for (const c of claims) {
			let structured = false;
			for (const [slot, value] of Object.entries(c.slots)) {
				if (value.state !== 'present' || !(slot in ROLE_CLASS)) continue;
				for (const ev of value.evidence ?? []) {
					if (ev.unit_version_id !== unit.unit_version_id) continue;
					marks.push({ start: ev.start, end: ev.end, cls: ROLE_CLASS[slot], claim: c });
					structured = true;
				}
			}
			for (const ev of c.modality_evidence ?? []) {
				if (ev.unit_version_id === unit.unit_version_id) marks.push({ start: ev.start, end: ev.end, cls: '', claim: c, cue: true });
			}
			if (!structured && c.quote?.unit_version_id === unit.unit_version_id) {
				marks.push({ start: c.quote.start, end: c.quote.end, cls: 'hl-other', claim: c });
			}
		}
		for (const g of gaps) if (g.unit_version_id === unit.unit_version_id) marks.push({ start: g.start, end: g.end, cls: '', gap: g });
		return marks;
	}

	function pieces(unit: Unit): Piece[] {
		const marks = marksFor(unit);
		const cuts = new Set([0, unit.text.length]);
		for (const m of marks) {
			cuts.add(Math.max(0, Math.min(unit.text.length, m.start)));
			cuts.add(Math.max(0, Math.min(unit.text.length, m.end)));
		}
		const points = [...cuts].sort((a, b) => a - b);
		const out: Piece[] = [];
		for (let i = 0; i < points.length - 1; i++) {
			const [a, b] = [points[i], points[i + 1]];
			if (a === b) continue;
			out.push({ text: unit.text.slice(a, b), marks: marks.filter((m) => m.start <= a && m.end >= b) });
		}
		return out;
	}

	function isFocused(m: Mark) {
		return !!focus && ((m.claim && focus.kind === 'claim' && focus.id === m.claim.id) || (m.gap && focus.kind === 'gap' && focus.id === m.gap.id));
	}

	function look(piece: Piece) {
		const fills = piece.marks.filter((m) => m.cls && m.claim);
		const lead = fills.find(isFocused) ?? fills.find((m) => m.claim?.decision !== 'reject') ?? fills[0];
		const cue = piece.marks.find((m) => m.cue && (isFocused(m) || !focus));
		const gap = piece.marks.find((m) => m.gap);
		return {
			cls: [
				lead ? `hl ${lead.cls}` : '',
				lead && isFocused(lead) ? 'on' : '',
				lead?.claim?.decision === 'reject' ? 'rejected' : '',
				cue ? 'cue' : '',
				gap ? (gap.gap?.decision ? 'gap done' : 'gap') : '',
				gap && isFocused(gap) ? 'gap-on' : ''
			].join(' ').trim(),
			target: (lead?.claim ? { kind: 'claim', id: lead.claim.id } : gap?.gap ? { kind: 'gap', id: gap.gap.id } : null) as Focus
		};
	}

	function flagsFor(unit: Unit) {
		const own = claims.filter((c) => (c.quote?.unit_version_id ?? '') === unit.unit_version_id).sort((a, b) => (a.quote?.start ?? 0) - (b.quote?.start ?? 0));
		const holes = gaps.filter((g) => g.unit_version_id === unit.unit_version_id);
		const notes = [
			...own.flatMap((c) => c.reasons.slice(0, 1).map((r) => ({ id: c.id, text: `${numbers.get(c.id)} · ${r}` }))),
			...holes.filter((g) => g.ai_note).map((g) => ({ id: g.id, text: g.ai_note! }))
		];
		return { own, holes, notes };
	}

	function flagLabel(c: Claim) {
		const state = c.decision === 'approve' ? t('review.approved') : c.decision === 'reject' ? t('review.rejected') : t('review.legend.undecided', { n: '' }).trim();
		return `${t('review.flag', { n: numbers.get(c.id) ?? 0 })}, ${state}`;
	}
</script>

<section class="article" id="article-{article.id.split('/').pop()}" aria-label={article.label}>
	{#each article.units as unit (unit.unit_version_id)}
		{@const flags = flagsFor(unit)}
		<div class="unit u-{unit.unit_type}" class:has-notes={flags.notes.length > 0}>
			<!-- Clicks on highlights are a mouse shortcut; the margin flags are the keyboard path to every norm. -->
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
			<p
				class="text"
				data-uv={unit.unit_version_id}
				onclick={(e) => {
					const target = (e.target as HTMLElement).closest<HTMLElement>('[data-target]');
					if (target && !getSelection()?.toString()) onfocus(JSON.parse(target.dataset.target!));
				}}
			>
				{#each pieces(unit) as piece, i (i)}
					{@const view = look(piece)}
					{#if view.cls}<span class={view.cls} data-target={view.target ? JSON.stringify(view.target) : undefined}>{piece.text}</span
						>{:else}{piece.text}{/if}
				{/each}
			</p>
			<div class="margin">
				{#each flags.notes as note (note.id)}<p class="pencil">{note.text}</p>{/each}
			</div>
			<div class="flags">
				{#each flags.own as c (c.id)}
					<button
						type="button"
						class="flag {c.decision ?? 'pending'}"
						aria-pressed={focus?.kind === 'claim' && focus.id === c.id}
						aria-label={flagLabel(c)}
						onclick={() => onfocus({ kind: 'claim', id: c.id })}>{numbers.get(c.id)}</button
					>
				{/each}
				{#each flags.holes as g (g.id)}
					<button
						type="button"
						class="flag gapflag"
						class:done={!!g.decision}
						aria-pressed={focus?.kind === 'gap' && focus.id === g.id}
						aria-label={t('review.flagGap')}
						onclick={() => onfocus({ kind: 'gap', id: g.id })}>?</button
					>
				{/each}
			</div>
		</div>
		{#if provenance && unit.unit_type === 'article'}<p class="provenance">{provenance}</p>{/if}
	{/each}
</section>

<style>
	.article {
		scroll-margin-top: calc(var(--topbar) + 72px);
	}
	.unit {
		position: relative;
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: 28px;
		align-items: start;
	}
	.unit.has-notes {
		grid-template-columns: minmax(0, 1fr) 150px;
	}
	.unit:not(.has-notes) .margin {
		display: none;
	}
	.margin {
		display: grid;
		gap: 6px;
		padding-top: 8px;
	}
	.margin .pencil {
		font: italic 13.5px/1.45 var(--serif);
		color: var(--muted);
		transform: rotate(-1deg);
	}
	.provenance {
		margin: -4px 0 14px;
		font-size: 13px;
		color: var(--muted);
	}
	.text {
		margin: 0 0 10px;
		font: 17.5px/1.9 var(--serif);
		white-space: pre-wrap;
		color: var(--ink);
	}
	.u-article .text {
		font-weight: 600;
	}
	.u-point .text {
		padding-left: 1.5em;
	}
	.hl {
		background: color-mix(in srgb, var(--hl) 62%, transparent);
		border-radius: 2px;
		box-decoration-break: clone;
		-webkit-box-decoration-break: clone;
		cursor: pointer;
		transition: background-color 0.2s var(--ease-out);
	}
	.hl:hover {
		background: var(--hl);
	}
	.hl.on {
		background: var(--hl);
		box-shadow: inset 0 -2px 0 rgb(0 0 0 / 0.38);
		animation: swipe 0.42s var(--ease-out);
	}
	.hl.rejected {
		background: transparent;
		text-decoration: line-through;
		text-decoration-color: var(--reject);
		color: var(--muted);
	}
	.cue {
		border-radius: 999px;
		box-shadow: 0 0 0 1.5px var(--ink-2);
		padding: 0 2px;
	}
	.gap {
		text-decoration: underline dotted var(--attention);
		text-decoration-thickness: 2px;
		text-underline-offset: 5px;
		cursor: pointer;
	}
	.gap.done {
		text-decoration-color: var(--rule-strong);
		color: var(--muted);
	}
	.gap-on {
		background: var(--attention-soft);
	}
	/* Paper flags are stuck to the sheet's right edge and overhang it. */
	.flags {
		position: absolute;
		top: 6px;
		right: calc(-1 * var(--sheet-pad-right, 40px) - 14px);
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.flag {
		width: 40px;
		height: 26px;
		border: 0;
		border-radius: 0 4px 4px 0;
		color: #fff;
		font: 600 13px/1 var(--sans);
		cursor: pointer;
		box-shadow: 0 1px 2px rgb(20 22 24 / 0.2), 0 3px 8px rgb(20 22 24 / 0.12);
		transform-origin: left center;
		transition: transform 0.18s var(--ease-out), box-shadow 0.18s var(--ease-out);
	}
	.flag.pending {
		background: var(--flag);
	}
	.flag.approve {
		background: var(--approve);
	}
	.flag.reject {
		background: var(--reject);
	}
	.flag.gapflag {
		background: var(--attention);
	}
	.flag.gapflag.done {
		background: var(--muted);
	}
	.flag:hover {
		transform: translateX(3px);
	}
	.flag[aria-pressed='true'] {
		transform: translateX(6px);
		box-shadow: 0 0 0 2px var(--paper), 0 0 0 3.5px var(--ink-2);
	}
	@keyframes swipe {
		from {
			background-size: 0% 100%;
			background-image: linear-gradient(var(--hl), var(--hl));
			background-repeat: no-repeat;
			background-color: transparent;
		}
		to {
			background-size: 100% 100%;
			background-image: linear-gradient(var(--hl), var(--hl));
			background-repeat: no-repeat;
		}
	}
</style>
