<script lang="ts">
	import { goto } from '$app/navigation';
	import { tick } from 'svelte';
	import { stagger } from 'animejs/utils';
	import Icon from './Icon.svelte';
	import Term from './Term.svelte';
	import Skeleton from './Skeleton.svelte';
	import { api } from '#lib/api.js';
	import { cachedAppState, loadAppState } from '#lib/app-state.svelte.js';
	import { t, formatDate, unitLabel } from '#lib/i18n/index.svelte.js';
	import { notify, act } from '#lib/toast.svelte.js';
	import { animate, rise, DUR, EASE } from '#lib/motion.js';
	import type { ChatSession } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	let { sessionId, preselect = [] }: { sessionId?: string; preselect?: string[] } = $props();

	const app = $derived(cachedAppState());
	let chat = $state<ChatSession | null>(null);
	let picked = $state<string[]>([]);
	let question = $state('');
	let mode = $state<'extractive' | 'llm'>('extractive');
	let consent = $state(false);
	let semantic = $state(true);
	let asking = $state(false);
	let pending = $state('');
	let conversation = $state<HTMLElement | null>(null);
	// Turns already there when the session opened appear with the page; later ones settle in as they arrive.
	let shownTurns = $state(Number.POSITIVE_INFINITY);

	$effect(() => {
		const sid = sessionId;
		Promise.all([loadAppState(), sid ? api<ChatSession>(`/api/chat/session?id=${encodeURIComponent(sid)}`) : Promise.resolve(null)])
			.then(([s, c]) => {
				chat = c;
				shownTurns = c?.turns.length ?? 0;
				picked = c ? c.bindings.map((b) => b.kb_id) : preselect.filter((id) => s.knowledge_bases.some((k) => k.id === id));
			})
			.catch((e) => notify(e.message, true));
	});

	const usable = $derived((app?.knowledge_bases ?? []).filter((k) => k.approved_claims > 0));
	const allPublic = $derived(!!chat && chat.bindings.every((b) => app?.knowledge_bases.find((k) => k.id === b.kb_id)?.data_class === 'public'));
	const semanticOn = $derived(!!app?.embedding_model && allPublic);

	function toggle(id: string, on: boolean) {
		picked = on ? [...picked, id].slice(0, 5) : picked.filter((x) => x !== id);
	}

	const start = () =>
		act(async () => {
			if (!picked.length) throw new Error(t('chat.pickOne'));
			const created = await api<{ id: string }>('/api/chat/start', { kb_ids: picked });
			await goto(`/chat/${created.id}`);
		});

	async function ask(event?: Event) {
		event?.preventDefault();
		if (!chat || !question.trim() || asking) return;
		asking = true;
		// The question shows at once with a placeholder answer, so the wait reads as work, not as nothing.
		pending = question.trim();
		await tick();
		conversation?.querySelector('.turn.pending')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
		const ok = await act(async () => {
			await api('/api/chat/ask', { session_id: chat!.id, question, mode, allow_public_transfer: mode === 'llm' && consent, semantic: semanticOn && semantic });
			const [next] = await Promise.all([api<ChatSession>(`/api/chat/session?id=${encodeURIComponent(chat!.id)}`), loadAppState()]);
			chat = next;
		});
		pending = '';
		asking = false;
		if (ok) question = '';
	}

	/** A new answer: the question stays where the placeholder put it; status, statements and slips settle in. */
	function arrive(node: HTMLElement) {
		const animation = animate(node.querySelectorAll(':scope > :not(.q)'), {
			opacity: [0, 1],
			transform: ['translateY(8px)', 'none'],
			duration: DUR.slow,
			delay: stagger(50),
			ease: EASE.out
		});
		return () => animation?.revert();
	}

	/** Opening a citation's details lets the facts drop in instead of popping. */
	function details(event: Event & { currentTarget: HTMLDetailsElement }) {
		const list = event.currentTarget.querySelector('dl');
		if (event.currentTarget.open && list) animate(list, { opacity: [0, 1], transform: ['translateY(-4px)', 'none'], duration: DUR.base, ease: EASE.out });
	}
</script>

<div class="chat">
	<aside class="setup">
		{#if sessionId}
			<!-- Inside a conversation the scope is fixed: show it, and offer a new conversation to change it. -->
			<section class="panel">
				<h2 class="heading">{t('chat.scope.session')}</h2>
				<p class="small muted">{t('chat.scope.sessionHint')}</p>
				{#if chat}
					<ul class="bound">
						{#each chat.bindings as b (b.kb_id)}
							<li><span class="kb-icon" aria-hidden="true"><Icon name="doc" size={16} /></span><span><strong>{b.kb_name ?? t('chat.deletedKb')}</strong><span class="small muted">{t('chat.revision', { r: b.revision_id.slice(0, 8) })}</span></span></li>
						{/each}
					</ul>
					<a class="btn" href="/chat?{chat.bindings.map((b) => `kb=${encodeURIComponent(b.kb_id)}`).join('&')}"><Icon name="plus" />{t('chat.new')}</a>
				{:else}
					<div class="pick" aria-hidden="true">
						{#each [0, 1] as i (i)}<div class="ghost-choice"><Skeleton width="16px" height="16px" radius="3px" /><div class="ghost-text"><Skeleton width="70%" height="14px" /><Skeleton width="44%" height="11px" /></div></div>{/each}
					</div>
				{/if}
			</section>
		{:else}
		<section class="panel">
			<h2 class="heading">{t('chat.scope')}</h2>
			<p class="small muted">{t('chat.scopeHint')}</p>
			{#if !app}
				<div class="pick" aria-hidden="true">
					{#each [0, 1, 2] as i (i)}
						<div class="ghost-choice"><Skeleton width="16px" height="16px" radius="3px" /><div class="ghost-text"><Skeleton width="70%" height="14px" /><Skeleton width="44%" height="11px" /></div></div>
					{/each}
				</div>
			{:else if !app.knowledge_bases.length}
				<p class="small muted">{t('chat.noKb')}</p>
			{:else}
				<div class="pick">
					{#each app.knowledge_bases as kb (kb.id)}
						<label class="choice">
							<input type="checkbox" checked={picked.includes(kb.id)} disabled={!kb.approved_claims || (!picked.includes(kb.id) && picked.length >= 5)} onchange={(e) => toggle(kb.id, e.currentTarget.checked)} />
							<strong>{kb.name}</strong>
							<span>{kb.approved_claims ? t('chat.norms', { n: kb.approved_claims }) : t('chat.normsNone')}</span>
						</label>
					{/each}
				</div>
				{#if usable.length}<button type="button" class="btn primary" onclick={start}>{t('chat.start')}</button>{/if}
			{/if}
		</section>
		{/if}
		{#if app?.chat_sessions.length}
			<section class="panel" in:rise={{ y: 6 }}>
				<h2 class="heading">{t('chat.previous')}</h2>
				<ul class="sessions">
					{#each app.chat_sessions as s (s.id)}
						<li>
							<a href="/chat/{s.id}" aria-current={chat?.id === s.id ? 'page' : undefined}>
								<span>{s.bindings.map((b) => b.kb_name ?? t('chat.deletedKb')).join(', ')}</span>
								<span class="small muted">{t('chat.turns', { date: formatDate(s.created_at), n: s.turns })}</span>
							</a>
						</li>
					{/each}
				</ul>
			</section>
		{/if}
	</aside>

	<div class="main">
		{#if !chat && sessionId}
			<div class="loading" aria-busy="true">
				<span class="visually-hidden" role="status">{t('common.loading')}</span>
				<div class="row"><Skeleton width="90px" height="12px" /><Skeleton width="150px" height="22px" radius="999px" /></div>
				<Skeleton width="60%" height="22px" />
				<div class="slip sheet ghost"><Skeleton width="40%" height="12px" /><Skeleton lines={3} height="15px" gap="12px" /></div>
			</div>
		{:else if !chat}
			<section class="panel intro">
				<div class="intro-text">
					<h2 class="subtitle">{t('chat.empty.title')}</h2>
					<p class="lead">{t('chat.empty.body')}</p>
				</div>
				<figure class="example" aria-hidden="true">
					<figcaption class="label">{t('chat.example')}</figcaption>
					<p class="ex-q serif" lang="vi">Lương thử việc ít nhất bao nhiêu phần trăm?</p>
					<div class="ex-slip">
						<p class="small"><span class="cid">[1]</span> <strong>Bộ luật Lao động 2019</strong> <span class="muted">· Điều 26</span></p>
						<p class="ex-quote serif" lang="vi">Tiền lương của người lao động trong thời gian thử việc do hai bên thỏa thuận nhưng <mark>ít nhất phải bằng 85% mức lương</mark> của công việc đó.</p>
					</div>
				</figure>
			</section>
		{:else}
			<p class="scope">
				<span class="label">{t('chat.on')}</span>
				{#each chat.bindings as b (b.kb_id)}<span class="chip">{b.kb_name ?? t('chat.deletedKb')}</span>{/each}
				<span class="small muted">{t('chat.frozen')} <Term key="revision" /></span>
			</p>
			<div class="conversation" bind:this={conversation}>
				{#if !chat.turns.length}
					<section class="panel samples">
						<p>{t('chat.noTurns')}</p>
						<div class="row">
							{#each ['chat.sample1', 'chat.sample2', 'chat.sample3'] as const as key (key)}
								<button type="button" class="btn small" lang="vi" onclick={() => (question = t(key))}>{t(key)}</button>
							{/each}
						</div>
					</section>
				{/if}
				{#each chat.turns as turn, i (i)}
					<article class="turn" {@attach i >= shownTurns && arrive}>
						<h3 class="q serif" lang="vi">{turn.question}</h3>
						<p class="status small">{t(`chat.status.${turn.status}` as MessageKey)}{turn.error_code ? ` ${t('chat.errorCode', { code: turn.error_code })}` : ''}</p>
						{#each turn.statements as s, j (j)}
							<p class="statement">{s.text} {#each s.citation_ids as cid (cid)}<sup>[{cid}]</sup>{/each}</p>
						{/each}
						{#each turn.citations as c (c.id)}
							<figure class="slip sheet">
								<figcaption class="small">
									<span class="cid">[{c.id}]</span>
									<strong>{c.title}</strong>
									<span class="muted">{unitLabel(c.evidence.unit_id)} · {t('chat.inKb', { names: c.sources.map((s) => s.kb_name).join(', ') })}</span>
									{#if c.edited}<span class="chip">{t('chat.edited')}</span>{/if}
									{#if c.dense_rank && !c.lexical_rank}<span class="chip">{t('chat.byMeaning')}</span>{/if}
									{#if c.synthetic}<span class="chip synthetic">{t('common.synthetic')}</span>{/if}
								</figcaption>
								<blockquote class="serif" lang="vi"><mark>{c.evidence.quote}</mark></blockquote>
								{#if c.scope.length}<p class="context serif" lang="vi"><Term key="context">{t('chat.context')}</Term>: {c.scope.map((s) => s.quote.trim()).join(' ')}</p>{/if}
								<details ontoggle={details}>
									<summary class="small">{t('chat.details')}</summary>
									<dl class="small">
										<dt>{t('chat.unit')}</dt><dd><code>{c.evidence.unit_id}</code></dd>
										<dt>{t('chat.offsets')}</dt><dd>{t('chat.offsetsValue', { start: c.evidence.start, end: c.evidence.end })}</dd>
										<dt>{t('chat.hash')}</dt><dd><code>{c.evidence.normalized_sha256}</code></dd>
										{#if c.similarity != null}<dt>{t('chat.similarity')}</dt><dd>{c.similarity}</dd>{/if}
										{#each c.sources as s (s.kb_name)}<dt>{s.kb_name}</dt><dd>{t('chat.revision', { r: s.revision })}</dd>{/each}
										{#if /^https:\/\//.test(c.source_url)}<dt>{t('chat.sourceLink')}</dt><dd><a href={c.source_url} target="_blank" rel="noopener noreferrer">{c.source_url}</a></dd>{/if}
									</dl>
								</details>
							</figure>
						{/each}
						<p class="pencil">{turn.mode === 'extractive' || turn.status === 'insufficient_evidence' ? t(turn.retrieval?.mode === 'hybrid' ? 'chat.note.hybrid' : 'chat.note.lexical') : turn.note}</p>
					</article>
				{/each}
				{#if pending}
					<article class="turn pending" aria-busy="true" in:rise={{ y: 10 }}>
						<h3 class="q serif" lang="vi">{pending}</h3>
						<p class="status small thinking" role="status"><span class="dots" aria-hidden="true"><i></i><i></i><i></i></span>{t('chat.thinking')}</p>
						<div class="slip sheet ghost" aria-hidden="true"><Skeleton width="46%" height="12px" /><Skeleton lines={3} height="15px" gap="12px" /></div>
					</article>
				{/if}
			</div>
			<form class="ask sheet" onsubmit={ask}>
				<label class="field">
					<span class="visually-hidden">{t('chat.question')}</span>
					<textarea rows="3" maxlength="1500" placeholder={t('chat.placeholder')} bind:value={question}
						onkeydown={(e) => e.key === 'Enter' && (e.ctrlKey || e.metaKey) && ask(e)}></textarea>
				</label>
				{#if app?.embedding_model}
					<label class="check small"><input type="checkbox" bind:checked={semantic} disabled={!semanticOn} />{allPublic ? t('chat.semantic', { model: app.embedding_model }) : t('chat.semanticPrivate')}</label>
				{/if}
				{#if mode === 'llm'}<label class="check small"><input type="checkbox" bind:checked={consent} />{t('chat.consent')}</label>{/if}
				<div class="askrow">
					<label class="mode"><span class="visually-hidden">{t('chat.mode')}</span>
						<select class="input" bind:value={mode}>
							<option value="extractive">{t('chat.mode.extractive')}</option>
							{#if app?.router_enabled}<option value="llm">{t('chat.mode.llm')}</option>{/if}
						</select>
					</label>
					<span class="small muted">{t('chat.sendHint')}</span>
					<button type="submit" class="btn primary send" disabled={asking || !question.trim()}><Icon name="arrow" />{t('chat.send')}</button>
				</div>
			</form>
		{/if}
	</div>
</div>

<style>
	.samples {
		display: grid;
		gap: 12px;
		padding: 18px 20px;
	}
	.samples > p {
		color: var(--ink-2);
	}
	.bound {
		list-style: none;
		margin: 2px 0 4px;
		padding: 0;
		display: grid;
		gap: 10px;
	}
	.bound li {
		display: grid;
		grid-template-columns: 30px minmax(0, 1fr);
		gap: 10px;
		align-items: center;
	}
	.bound li > span:last-child {
		display: grid;
		gap: 1px;
		min-width: 0;
	}
	.bound strong {
		font-weight: 600;
		overflow-wrap: anywhere;
	}
	.kb-icon {
		display: grid;
		place-items: center;
		width: 30px;
		height: 30px;
		border-radius: 6px;
		background: var(--desk);
		color: var(--ink-2);
	}
	.chat {
		display: grid;
		grid-template-columns: 300px minmax(0, 1fr);
		gap: var(--space-6);
		align-items: start;
	}
	.setup {
		position: sticky;
		top: calc(var(--topbar) + 16px);
		display: grid;
		gap: var(--space-4);
	}
	.setup .panel {
		display: grid;
		gap: 10px;
		padding: 20px;
	}
	.pick {
		display: grid;
		gap: 8px;
	}
	.ghost-choice {
		display: grid;
		grid-template-columns: 16px minmax(0, 1fr);
		gap: 10px;
		padding: 16px;
		border: 1px solid var(--rule);
		border-radius: var(--r-panel);
	}
	.ghost-text {
		display: grid;
		gap: 7px;
	}
	.sessions {
		list-style: none;
		margin: 0 -10px;
		padding: 0;
		display: grid;
		gap: 2px;
	}
	.sessions a {
		display: grid;
		gap: 2px;
		padding: 8px 10px;
		border-radius: var(--r-control);
		color: var(--ink);
		text-decoration: none;
		transition: background-color var(--dur-fast) ease;
	}
	.sessions a:hover {
		background: var(--desk);
	}
	.sessions a[aria-current='page'] {
		background: var(--desk);
		font-weight: 600;
	}
	.main {
		display: grid;
		gap: 18px;
		min-width: 0;
	}
	/* Empty state: the same paper and edges as the scope panel beside it, with a specimen answer. */
	.intro {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr);
		gap: var(--space-6) var(--space-8);
		align-items: start;
		padding: 24px 28px;
	}
	.intro-text {
		display: grid;
		gap: 10px;
		padding-top: 2px;
	}
	.example {
		margin: 0;
		display: grid;
		gap: 10px;
		padding: 16px 18px 18px;
		background: var(--desk);
		border-radius: var(--r-control);
	}
	.ex-q {
		font-size: 17px;
		font-weight: 600;
		line-height: 1.4;
	}
	.ex-slip {
		display: grid;
		gap: 6px;
		padding: 12px 14px;
		background: var(--paper);
		border-radius: var(--r-sheet);
		box-shadow: var(--shadow-sheet);
	}
	.ex-quote {
		font-size: 15.5px;
		line-height: 1.7;
	}
	.ex-quote mark {
		background: rgb(42 45 48 / 0.06);
		box-shadow: inset 0 -1.5px 0 var(--ink-2);
		color: inherit;
		padding: 1px 2px;
		border-radius: 2px;
	}
	.loading {
		display: grid;
		gap: 16px;
	}
	.scope {
		display: flex;
		gap: 8px;
		flex-wrap: wrap;
		align-items: center;
	}
	.conversation {
		display: grid;
		gap: 32px;
	}
	.turn {
		display: grid;
		gap: 10px;
		scroll-margin-top: calc(var(--topbar) + 16px);
	}
	.q {
		font-size: 21px;
		line-height: 1.4;
		font-weight: 600;
		max-width: 60ch;
	}
	.status {
		color: var(--ink-2);
		font-weight: 500;
	}
	.statement {
		max-width: 75ch;
	}
	.statement sup {
		color: var(--focus);
		font-weight: 600;
	}
	.thinking {
		display: flex;
		align-items: center;
		gap: 10px;
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
	.slip {
		margin: 0;
		padding: 16px 20px;
		display: grid;
		gap: 10px;
	}
	.slip.ghost {
		gap: 14px;
		padding: 18px 20px 20px;
	}
	figcaption {
		display: flex;
		gap: 4px 10px;
		flex-wrap: wrap;
		align-items: baseline;
	}
	.example figcaption {
		display: block;
	}
	.cid {
		font-weight: 600;
		color: var(--focus);
	}
	blockquote {
		margin: 0;
		font-size: 17px;
		line-height: 1.8;
		max-width: 75ch;
	}
	/* A citation is marked in graphite pencil: yellow already means the norm's subject. */
	blockquote mark {
		background: rgb(42 45 48 / 0.06);
		box-shadow: inset 0 -1.5px 0 var(--ink-2);
		color: inherit;
		padding: 1px 2px;
		border-radius: 2px;
		box-decoration-break: clone;
		-webkit-box-decoration-break: clone;
	}
	.context {
		color: var(--muted);
		font-size: 15px;
		max-width: 75ch;
	}
	details dl {
		display: grid;
		grid-template-columns: 150px minmax(0, 1fr);
		gap: 4px 12px;
		margin: 8px 0 0;
	}
	details dd {
		margin: 0;
		overflow-wrap: anywhere;
	}
	summary {
		cursor: pointer;
		color: var(--ink-2);
		width: fit-content;
	}
	summary:hover {
		color: var(--ink);
	}
	.ask {
		position: sticky;
		bottom: 16px;
		padding: 14px 16px;
		display: grid;
		gap: 10px;
		box-shadow: var(--shadow-pop);
	}
	.ask textarea {
		min-height: 76px;
	}
	.askrow {
		display: flex;
		gap: 12px;
		align-items: center;
		flex-wrap: wrap;
	}
	.askrow .muted {
		margin-left: auto;
	}
	.mode select {
		width: auto;
	}
	.send :global(svg) {
		transition: transform var(--dur-base) var(--ease-out);
	}
	@media (hover: hover) {
		.send:hover:not(:disabled) :global(svg) {
			transform: translateX(2px);
		}
	}
	@media (max-width: 1180px) {
		.intro {
			grid-template-columns: 1fr;
		}
	}
	@media (max-width: 900px) {
		.chat {
			grid-template-columns: 1fr;
		}
		.setup {
			position: static;
		}
		.intro {
			padding: 20px;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.dots i {
			animation: none;
			opacity: 0.6;
		}
	}
</style>
