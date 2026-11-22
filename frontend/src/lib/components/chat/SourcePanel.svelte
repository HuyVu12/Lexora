<script lang="ts">
	import { tick } from 'svelte';
	import Icon from '../Icon.svelte';
	import Term from '../Term.svelte';
	import Skeleton from '../Skeleton.svelte';
	import { api } from '#lib/api.js';
	import { t, unitLabel } from '#lib/i18n/index.svelte.js';
	import { slideIn } from './chat.js';
	import type { ChatSource, Citation } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	// The source of one citation, beside the conversation (a bottom sheet on a phone): the document, its
	// Chapter/Article/Clause path, the bases holding it, and the cited sentence highlighted inside the exact text
	// of its unit in the conversation's pinned revision. Only the highlighted sentence is approved evidence.
	let {
		sessionId,
		turn,
		citation,
		number,
		onclose
	}: { sessionId: string; turn: number; citation: Citation; number: number; onclose: () => void } = $props();

	const cache = new Map<string, Promise<ChatSource>>();
	let source = $state<ChatSource | null>(null);
	let failed = $state('');
	let textEl = $state<HTMLElement | null>(null);
	let closeBtn = $state<HTMLButtonElement | null>(null);

	$effect(() => {
		const key = `${sessionId}:${turn}:${citation.id}`;
		source = null;
		failed = '';
		if (!cache.has(key)) {
			const request = api<ChatSource>(`/api/chat/source?session_id=${encodeURIComponent(sessionId)}&turn=${turn}&citation=${encodeURIComponent(citation.id)}`);
			request.catch(() => cache.delete(key));
			cache.set(key, request);
		}
		cache
			.get(key)!
			.then(async (value) => {
				if (key !== `${sessionId}:${turn}:${citation.id}`) return;
				source = value;
				await tick();
				// Bring the highlighted sentence into view inside a long unit.
				const mark = textEl?.querySelector('mark');
				if (mark && textEl && mark.offsetTop > textEl.clientHeight * 0.6) mark.scrollIntoView({ block: 'center' });
			})
			.catch((e) => (failed = e.message));
	});

	$effect(() => {
		closeBtn?.focus({ preventScroll: true });
	});

	const crumb = (p: ChatSource['path'][number]) => {
		const key = `unit.${p.unit_type}` as MessageKey;
		const name = `${t(key)} ${p.label ?? ''}`.trim();
		const head = name.charAt(0).toUpperCase() + name.slice(1);
		return p.heading ? `${head}. ${p.heading}` : head;
	};
	const kbNames = $derived(citation.sources.map((s) => s.kb_name).join(', '));
	// Beside the conversation it slides in from the right; as a phone's bottom sheet, up from the bottom.
	const narrow = typeof window !== 'undefined' && !!window.matchMedia?.('(max-width: 900px)').matches;
</script>

<button type="button" class="backdrop" aria-label={t('chat.source.close')} tabindex="-1" onclick={onclose}></button>
<aside class="source" data-tour="chat-source" aria-labelledby="source-title" in:slideIn={narrow ? { y: 60 } : { x: 18 }} out:slideIn={narrow ? { y: 60, duration: 160 } : { x: 12, duration: 140 }}>
	<header class="head">
		<p class="label" id="source-title">{t('chat.source.title', { n: number })}</p>
		<button type="button" class="close" bind:this={closeBtn} aria-label={t('chat.source.close')} onclick={onclose}><Icon name="x" size={18} /></button>
	</header>
	<div class="scroll" bind:this={textEl}>
		<h2 class="doc serif">{citation.title}</h2>
		{#if source}
			<ol class="path" aria-label={t('chat.source.path')}>
				{#each source.path as p (p.unit_id)}<li>{crumb(p)}</li>{/each}
			</ol>
		{:else if !failed}
			<p class="path-ghost"><Skeleton width="62%" height="13px" /></p>
		{:else}
			<p class="small muted">{unitLabel(citation.evidence.unit_id)}</p>
		{/if}
		<p class="kbs small">
			<span>{t('chat.inKb', { names: kbNames })}</span>
			{#if citation.synthetic}<span class="chip synthetic">{t('common.synthetic')}</span>{/if}
			{#if citation.edited}<span class="chip">{t('chat.edited')}</span>{/if}
			{#if citation.dense_rank && !citation.lexical_rank}<span class="chip">{t('chat.byMeaning')}</span>{/if}
		</p>

		<div class="text serif" lang="vi">
			{#if source}
				{source.text.slice(0, source.start)}<mark>{source.text.slice(source.start, source.end)}</mark>{source.text.slice(source.end)}
			{:else}
				<mark>{citation.evidence.quote}</mark>
				{#if !failed}<span class="text-ghost" aria-hidden="true"><Skeleton lines={3} height="14px" gap="11px" last="55%" /></span>{/if}
			{/if}
		</div>
		<p class="note small">{t('chat.source.note')}</p>
		{#if failed}<p class="small error" role="alert">{failed}</p>{/if}

		{#if citation.scope.length}
			<p class="context serif" lang="vi"><Term key="context">{t('chat.context')}</Term>: {citation.scope.map((s) => s.quote.trim()).join(' ')}</p>
		{/if}

		<div class="links">
			{#if source}
				<a class="btn small" href="/kb/{source.kb_id}/graph"><Icon name="graph" />{t('chat.source.graph')}</a>
			{/if}
			{#if /^https:\/\//.test(citation.source_url)}
				<a class="btn small quiet" href={citation.source_url} target="_blank" rel="noopener noreferrer"><Icon name="link" />{t('chat.sourceLink')}</a>
			{/if}
		</div>

		<details>
			<summary class="small">{t('chat.details')}</summary>
			<dl class="small">
				<dt>{t('chat.unit')}</dt><dd><code>{citation.evidence.unit_id}</code></dd>
				<dt>{t('chat.offsets')}</dt><dd>{t('chat.offsetsValue', { start: citation.evidence.start, end: citation.evidence.end })}</dd>
				<dt>{t('chat.hash')}</dt><dd><code>{citation.evidence.normalized_sha256}</code></dd>
				{#if citation.similarity != null}<dt>{t('chat.similarity')}</dt><dd>{citation.similarity}</dd>{/if}
				{#each citation.sources as s (s.kb_name)}<dt>{s.kb_name}</dt><dd><Term key="revision">{t('chat.revision', { r: s.revision.slice(0, 8) })}</Term></dd>{/each}
			</dl>
		</details>
	</div>
</aside>

<style>
	.backdrop {
		display: none;
	}
	.source {
		display: flex;
		flex-direction: column;
		min-height: 0;
		height: 100%;
		background: var(--paper);
		border-left: 1px solid var(--rule);
	}
	.head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		min-height: 52px;
		padding: 8px 10px 8px 22px;
		border-bottom: 1px solid var(--rule);
	}
	.label {
		font: 600 13px/1.4 var(--sans);
		color: var(--muted);
	}
	.close {
		display: grid;
		place-items: center;
		width: 34px;
		height: 34px;
		padding: 0;
		border: 0;
		border-radius: var(--r-control);
		background: transparent;
		color: var(--ink-2);
		cursor: pointer;
		transition: background-color var(--dur-fast) ease;
	}
	.close:hover {
		background: var(--desk);
	}
	.scroll {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: 12px;
		padding: 20px 22px 32px;
	}
	.doc {
		font-size: 19px;
		line-height: 1.35;
		font-weight: 600;
		overflow-wrap: anywhere;
	}
	.path {
		display: flex;
		flex-wrap: wrap;
		gap: 2px 0;
		margin: -4px 0 0;
		padding: 0;
		list-style: none;
		font-size: 13.5px;
		color: var(--ink-2);
	}
	.path li + li::before {
		content: '›';
		margin: 0 8px;
		color: var(--rule-strong);
	}
	.path li:last-child {
		font-weight: 600;
		color: var(--ink);
	}
	.path-ghost {
		margin-top: -2px;
	}
	.kbs {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px 8px;
		color: var(--muted);
	}
	.text {
		margin-top: 4px;
		font-size: 16.5px;
		line-height: 1.8;
		white-space: pre-line;
		overflow-wrap: anywhere;
		color: var(--muted);
	}
	/* The cited sentence in reference blue, like its chip in the answer (yellow means the norm's subject elsewhere). */
	.text mark {
		color: var(--ink);
		background: rgb(47 95 196 / 0.11);
		padding: 2px 1px;
		border-radius: 2px;
		box-decoration-break: clone;
		-webkit-box-decoration-break: clone;
	}
	.text-ghost {
		display: block;
		margin-top: 12px;
	}
	.note {
		color: var(--muted);
		line-height: 1.5;
	}
	.context {
		color: var(--muted);
		font-size: 15px;
		line-height: 1.6;
	}
	.links {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin-top: 2px;
	}
	.links:empty {
		display: none;
	}
	details {
		margin-top: 4px;
		padding-top: 12px;
		border-top: 1px solid var(--rule);
	}
	summary {
		cursor: pointer;
		color: var(--ink-2);
		width: fit-content;
	}
	summary:hover {
		color: var(--ink);
	}
	dl {
		display: grid;
		grid-template-columns: 120px minmax(0, 1fr);
		gap: 6px 12px;
		margin: 10px 0 0;
	}
	dd {
		margin: 0;
		overflow-wrap: anywhere;
	}
	dt {
		color: var(--muted);
	}
	.error {
		color: var(--reject);
	}
	/* Phone: a bottom sheet over a dimmed conversation. */
	@media (max-width: 900px) {
		.backdrop {
			display: block;
			position: fixed;
			inset: 0;
			z-index: 60;
			border: 0;
			padding: 0;
			background: rgb(20 22 24 / 0.32);
			cursor: default;
		}
		.source {
			position: fixed;
			left: 0;
			right: 0;
			bottom: 0;
			z-index: 61;
			height: auto;
			max-height: 82dvh;
			border-left: 0;
			border-radius: 14px 14px 0 0;
			box-shadow: var(--shadow-pop);
		}
		.head {
			padding-left: 18px;
		}
		.scroll {
			padding: 16px 18px calc(24px + env(safe-area-inset-bottom));
		}
	}
</style>
