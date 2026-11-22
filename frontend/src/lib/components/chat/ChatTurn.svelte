<script lang="ts">
	import { stagger } from 'animejs/utils';
	import Icon from '../Icon.svelte';
	import LexoraMark from './LexoraMark.svelte';
	import { t, unitLabel } from '#lib/i18n/index.svelte.js';
	import { animate, DUR, EASE } from '#lib/motion.js';
	import { citationNumber } from './chat.js';
	import type { Turn } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	// One exchange: the question in a soft bubble on the right, the answer on the left beside the Lexora mark.
	// Model answers carry inline citation chips; quote answers list the approved sentences themselves. Every
	// citation opens the source panel. A turn that has just arrived reveals its parts one after another.
	let {
		turn,
		index,
		fresh = false,
		active = null,
		kbCount,
		stage = null,
		oncite,
		onedit,
		oncopy
	}: {
		turn: Turn;
		index: number;
		fresh?: boolean;
		active?: string | null;
		kbCount: number;
		/** While the question waits for its answer: the real stage of the work, shown instead of an answer. */
		stage?: string | null;
		oncite: (index: number, citationId: string, from: HTMLElement) => void;
		onedit: (question: string) => void;
		oncopy: (turn: Turn) => Promise<boolean>;
	} = $props();

	// The copy button answers in place (a check for a moment) instead of a toast over the composer.
	let copied = $state(false);
	let copyTimer: ReturnType<typeof setTimeout> | undefined;
	async function copy() {
		if (!(await oncopy(turn))) return;
		copied = true;
		clearTimeout(copyTimer);
		copyTimer = setTimeout(() => (copied = false), 1600);
	}

	const answered = $derived(turn.status === 'answered' && turn.statements.length > 0);
	const quotes = $derived(turn.status !== 'answered' && turn.citations.length > 0);
	const none = $derived(turn.status === 'insufficient_evidence');
	// Statuses of the model path that are not an answer: say so plainly, then show what was found.
	const notice = $derived(!['answered', 'sources_found', 'insufficient_evidence'].includes(turn.status));
	const extractive = $derived(turn.mode !== 'llm');

	/** The answer's parts settle in one after another: transform and opacity only, skipped under reduced motion. */
	function reveal(node: HTMLElement) {
		if (!fresh) return;
		const animation = animate(node.querySelectorAll('.reveal'), {
			opacity: [0, 1],
			transform: ['translateY(6px)', 'none'],
			duration: DUR.slow,
			delay: stagger(70),
			ease: EASE.out
		});
		return () => animation?.revert();
	}

	const isActive = (cid: string) => active === `${index}:${cid}`;
</script>

<article class="turn" aria-label={t('chat.turnLabel', { n: index + 1 })} aria-busy={stage ? 'true' : undefined}>
	<div class="q-row">
		{#if !stage}<button type="button" class="icon-btn edit" aria-label={t('chat.edit')} title={t('chat.edit')} onclick={() => onedit(turn.question)}><Icon name="edit" size={16} /></button>{/if}
		<p class="bubble" lang="vi"><span class="visually-hidden">{t('chat.you')}: </span>{turn.question}</p>
	</div>

	<div class="answer">
		<LexoraMark />
		{#if stage}
			<p class="stage" role="status"><span class="dots" aria-hidden="true"><i></i><i></i><i></i></span>{stage}</p>
		{:else}
		<div class="body" {@attach reveal}>
			<span class="visually-hidden">{t('chat.assistant')}: </span>
			{#if answered}
				{#each turn.statements as s, j (j)}
					<p class="statement reveal">
						{s.text}{#each s.citation_ids as cid (cid)}{@const n = citationNumber(turn, cid)}<button
								type="button"
								class="cite"
								class:on={isActive(cid)}
								aria-label={t('chat.cite', { n })}
								aria-pressed={isActive(cid)}
								onclick={(e) => oncite(index, cid, e.currentTarget)}>{n}</button
							>{/each}
					</p>
				{/each}
			{:else if none}
				<div class="none reveal" role="note">
					<span class="none-icon" aria-hidden="true"><Icon name="search" size={16} /></span>
					<div>
						<p class="none-title">{t('chat.noEvidence.title')}</p>
						<p class="none-body">{t('chat.noEvidence.body', { n: kbCount })}</p>
					</div>
				</div>
			{:else if notice}
				<p class="notice-line reveal"><Icon name="warn" size={16} />{t(`chat.status.${turn.status}` as MessageKey)}{turn.error_code ? ` ${t('chat.errorCode', { code: turn.error_code })}` : ''}</p>
			{/if}

			{#if quotes}
				{#if !notice}<p class="lead reveal">{t('chat.found', { n: turn.citations.length })}</p>{/if}
				<ol class="quotes">
					{#each turn.citations as c, k (c.id)}
						<li class="quote reveal" class:on={isActive(c.id)}>
							<span class="num" aria-hidden="true">{k + 1}</span>
							<div class="quote-body">
								<p class="quote-text serif" lang="vi">{c.evidence.quote.trim()}</p>
								<button type="button" class="where" aria-pressed={isActive(c.id)} aria-label={t('chat.cite.where', { n: k + 1, title: c.title, unit: unitLabel(c.evidence.unit_id) })} onclick={(e) => oncite(index, c.id, e.currentTarget)}>
									<span class="doc">{c.title}</span>{#if unitLabel(c.evidence.unit_id)}<span class="unit">{unitLabel(c.evidence.unit_id)}</span>{/if}<span class="go"><Icon name="chevron" size={14} /></span>
								</button>
								{#if c.synthetic || c.edited || (c.dense_rank && !c.lexical_rank)}
									<p class="tags">
										{#if c.synthetic}<span class="chip synthetic">{t('common.synthetic')}</span>{/if}
										{#if c.edited}<span class="chip">{t('chat.edited')}</span>{/if}
										{#if c.dense_rank && !c.lexical_rank}<span class="chip">{t('chat.byMeaning')}</span>{/if}
									</p>
								{/if}
							</div>
						</li>
					{/each}
				</ol>
			{:else if answered && turn.citations.length}
				<div class="sources reveal">
					<p class="sources-label">{t('chat.sources')}</p>
					<ol>
						{#each turn.citations as c, k (c.id)}
							<li>
								<button type="button" class="source-row" class:on={isActive(c.id)} aria-pressed={isActive(c.id)} onclick={(e) => oncite(index, c.id, e.currentTarget)}>
									<span class="num" aria-hidden="true">{k + 1}</span>
									<span class="source-text">
										<span class="source-where"><strong>{c.title}</strong>{#if unitLabel(c.evidence.unit_id)} · {unitLabel(c.evidence.unit_id)}{/if}{#if c.synthetic} <span class="chip synthetic">{t('common.synthetic')}</span>{/if}</span>
										<span class="source-quote serif" lang="vi">{c.evidence.quote.trim()}</span>
									</span>
								</button>
							</li>
						{/each}
					</ol>
				</div>
			{/if}

			<div class="foot reveal">
				<button type="button" class="icon-btn" class:done={copied} aria-label={copied ? t('chat.copied') : t('chat.copy')} title={t('chat.copy')} onclick={copy}><Icon name={copied ? 'check' : 'copy'} size={16} /></button>
				<span class="meta">
					{#if extractive || none}
						{t(turn.retrieval?.mode === 'hybrid' ? 'chat.meta.hybrid' : 'chat.meta.lexical')}
					{:else}
						{turn.note}
					{/if}
				</span>
			</div>
		</div>
		{/if}
	</div>
</article>

<style>
	.turn {
		display: grid;
		gap: 22px;
	}
	.q-row {
		display: flex;
		justify-content: flex-end;
		align-items: flex-start;
		gap: 6px;
		padding-left: 12%;
	}
	.bubble {
		max-width: 100%;
		padding: 10px 16px;
		background: #eff0ef;
		border-radius: 18px 18px 4px 18px;
		font-size: 15.5px;
		line-height: 1.55;
		white-space: pre-wrap;
		overflow-wrap: anywhere;
	}
	.icon-btn {
		display: grid;
		place-items: center;
		flex: none;
		width: 30px;
		height: 30px;
		padding: 0;
		border: 0;
		border-radius: var(--r-control);
		background: transparent;
		color: var(--muted);
		cursor: pointer;
		transition:
			background-color var(--dur-fast) ease,
			color var(--dur-fast) ease,
			opacity var(--dur-fast) ease;
	}
	.icon-btn:hover {
		background: var(--desk);
		color: var(--ink);
	}
	.icon-btn:active {
		transform: scale(0.94);
	}
	/* Edit appears beside the question it belongs to when the pointer is on it; touch and keyboard always reach it. */
	.edit {
		margin-top: 5px;
		opacity: 0;
	}
	.q-row:hover .edit,
	.edit:focus-visible {
		opacity: 1;
	}
	@media (hover: none) {
		.edit {
			opacity: 1;
		}
	}
	.answer {
		display: grid;
		grid-template-columns: 26px minmax(0, 1fr);
		gap: 14px;
		align-items: start;
	}
	.answer > :global(.mark) {
		margin-top: 1px;
	}
	.body {
		display: grid;
		gap: 12px;
		min-width: 0;
		padding-top: 2px;
	}
	.statement {
		font-size: 15.5px;
		line-height: 1.72;
		overflow-wrap: anywhere;
	}
	.lead {
		font-size: 15.5px;
		line-height: 1.6;
		color: var(--ink);
	}
	/* Citation chips: small numbered tabs inside the answer text, blue like every reference in Lexora. */
	.cite {
		display: inline-grid;
		place-items: center;
		min-width: 19px;
		height: 18px;
		margin: 0 0 0 3px;
		padding: 0 5px;
		border: 0;
		border-radius: 5px;
		background: rgb(47 95 196 / 0.1);
		color: var(--focus);
		font: 600 11.5px/1 var(--sans);
		vertical-align: 0.14em;
		cursor: pointer;
		transition:
			background-color var(--dur-fast) ease,
			color var(--dur-fast) ease,
			transform var(--dur-fast) var(--ease-out);
	}
	.cite + .cite {
		margin-left: 2px;
	}
	.cite:hover {
		background: rgb(47 95 196 / 0.18);
	}
	.cite.on {
		background: var(--focus);
		color: #fff;
	}
	.cite:active {
		transform: scale(0.92);
	}
	.quotes,
	.sources ol {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 14px;
	}
	.quote {
		display: grid;
		grid-template-columns: 22px minmax(0, 1fr);
		gap: 10px;
		align-items: start;
	}
	.num {
		display: grid;
		place-items: center;
		width: 20px;
		height: 20px;
		margin-top: 3px;
		border-radius: 5px;
		background: rgb(47 95 196 / 0.1);
		color: var(--focus);
		font: 600 11.5px/1 var(--sans);
		transition:
			background-color var(--dur-fast) ease,
			color var(--dur-fast) ease;
	}
	.quote.on .num,
	.source-row.on .num {
		background: var(--focus);
		color: #fff;
	}
	.quote-body {
		display: grid;
		gap: 5px;
		min-width: 0;
		padding-left: 12px;
		border-left: 2px solid var(--rule);
		transition: border-color var(--dur-fast) ease;
	}
	.quote.on .quote-body {
		border-left-color: var(--focus);
	}
	.quote-text {
		font-size: 16px;
		line-height: 1.68;
		color: var(--ink);
		overflow-wrap: anywhere;
	}
	/* Document and place read as one line of text that wraps like text, the chevron riding at its end. */
	.where {
		display: block;
		width: fit-content;
		max-width: 100%;
		padding: 2px 6px;
		margin-left: -6px;
		border: 0;
		border-radius: 5px;
		background: transparent;
		color: var(--muted);
		font-size: 13px;
		line-height: 1.45;
		text-align: left;
		cursor: pointer;
		transition:
			background-color var(--dur-fast) ease,
			color var(--dur-fast) ease;
	}
	.where .doc {
		font-weight: 500;
		color: var(--ink-2);
	}
	.where .unit {
		white-space: nowrap;
	}
	.where .unit::before {
		content: '·';
		margin: 0 7px;
		color: var(--rule-strong);
	}
	.go {
		display: inline-block;
		margin-left: 4px;
		vertical-align: -2px;
		color: var(--muted);
	}
	.go :global(svg) {
		display: block;
		transform: rotate(-90deg);
		transition: transform var(--dur-base) var(--ease-out);
	}
	@media (hover: hover) {
		.where:hover .go :global(svg) {
			transform: rotate(-90deg) translateY(2px);
		}
	}
	.icon-btn.done {
		color: var(--approve);
	}
	.where:hover {
		background: var(--desk);
		color: var(--ink);
	}
	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.sources {
		display: grid;
		gap: 8px;
		margin-top: 2px;
	}
	.sources-label {
		font: 600 12px/1.4 var(--sans);
		color: var(--muted);
	}
	.sources ol {
		gap: 4px;
	}
	.source-row {
		display: grid;
		grid-template-columns: 22px minmax(0, 1fr);
		gap: 10px;
		width: 100%;
		padding: 8px 10px 8px 8px;
		border: 1px solid var(--rule);
		border-radius: var(--r-panel);
		background: var(--paper);
		color: var(--ink);
		text-align: left;
		cursor: pointer;
		transition:
			border-color var(--dur-fast) ease,
			background-color var(--dur-fast) ease;
	}
	.source-row:hover {
		border-color: var(--rule-strong);
	}
	.source-row.on {
		border-color: var(--focus);
	}
	.source-row .num {
		margin-top: 1px;
	}
	.source-text {
		display: grid;
		gap: 2px;
		min-width: 0;
	}
	.source-where {
		font-size: 13px;
		color: var(--muted);
	}
	.source-where strong {
		font-weight: 500;
		color: var(--ink-2);
	}
	.source-quote {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
		font-size: 14.5px;
		line-height: 1.55;
	}
	/* No evidence is an answer too: said plainly, in the same voice, without alarm colours. */
	.none {
		display: grid;
		grid-template-columns: 30px minmax(0, 1fr);
		gap: 12px;
		align-items: start;
		padding: 12px 14px;
		border: 1px dashed var(--rule-strong);
		border-radius: var(--r-panel);
	}
	.none-icon {
		display: grid;
		place-items: center;
		width: 30px;
		height: 30px;
		border-radius: 50%;
		background: var(--desk);
		color: var(--ink-2);
	}
	.none-title {
		font-weight: 600;
		line-height: 1.5;
	}
	.none-body {
		margin-top: 2px;
		color: var(--ink-2);
		font-size: 14px;
		line-height: 1.55;
	}
	.notice-line {
		display: flex;
		align-items: center;
		gap: 8px;
		font-weight: 500;
		color: var(--attention);
	}
	.notice-line :global(svg) {
		flex: none;
	}
	.stage {
		display: flex;
		align-items: center;
		gap: 10px;
		min-height: 28px;
		color: var(--ink-2);
		font-size: 14.5px;
	}
	.dots {
		display: inline-flex;
		gap: 4px;
	}
	.dots i {
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background: var(--ink-2);
		animation: think 1s var(--ease-in-out) infinite;
	}
	.dots i:nth-child(2) {
		animation-delay: 0.15s;
	}
	.dots i:nth-child(3) {
		animation-delay: 0.3s;
	}
	@keyframes think {
		0%,
		100% {
			opacity: 0.25;
			transform: translateY(0);
		}
		40% {
			opacity: 1;
			transform: translateY(-3px);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.dots i {
			animation: none;
			opacity: 0.6;
		}
	}
	.foot {
		display: flex;
		align-items: center;
		gap: 6px;
		margin: -2px 0 0 -6px;
	}
	.meta {
		font-size: 12.5px;
		line-height: 1.45;
		color: var(--muted);
	}
	@media (max-width: 640px) {
		.q-row {
			padding-left: 8%;
		}
		/* A phone has no room for an avatar column; the answer starts at the edge, as in phone chat apps. */
		.answer {
			grid-template-columns: minmax(0, 1fr);
		}
		.answer > :global(.mark) {
			display: none;
		}
		.quote-text {
			font-size: 16px;
		}
	}
</style>
