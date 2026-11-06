<script lang="ts">
	import { goto } from '$app/navigation';
	import { tick } from 'svelte';
	import Icon from './Icon.svelte';
	import Term from './Term.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDate, unitLabel } from '#lib/i18n/index.svelte.js';
	import { notify, act } from '#lib/toast.svelte.js';
	import type { AppState, ChatSession } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	let { sessionId, preselect = [] }: { sessionId?: string; preselect?: string[] } = $props();

	let app = $state<AppState | null>(null);
	let chat = $state<ChatSession | null>(null);
	let picked = $state<string[]>([]);
	let question = $state('');
	let mode = $state<'extractive' | 'llm'>('extractive');
	let consent = $state(false);
	let semantic = $state(true);
	let asking = $state(false);
	let conversation = $state<HTMLElement | null>(null);

	$effect(() => {
		const sid = sessionId;
		Promise.all([api<AppState>('/api/state'), sid ? api<ChatSession>(`/api/chat/session?id=${encodeURIComponent(sid)}`) : Promise.resolve(null)])
			.then(([s, c]) => {
				app = s;
				chat = c;
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
		if (!chat || !question.trim()) return;
		asking = true;
		const ok = await act(async () => {
			await api('/api/chat/ask', { session_id: chat!.id, question, mode, allow_public_transfer: mode === 'llm' && consent, semantic: semanticOn && semantic });
			[chat, app] = await Promise.all([api<ChatSession>(`/api/chat/session?id=${encodeURIComponent(chat!.id)}`), api<AppState>('/api/state')]);
		});
		asking = false;
		if (ok) {
			question = '';
			await tick();
			conversation?.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'start' });
		}
	}
</script>

<div class="chat">
	<aside class="setup">
		<section class="panel">
			<h2 class="heading">{t('chat.scope')}</h2>
			<p class="small muted">{t('chat.scopeHint')}</p>
			{#if app && !app.knowledge_bases.length}
				<p class="small muted">{t('chat.noKb')}</p>
			{:else if app}
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
		{#if app?.chat_sessions.length}
			<section class="panel">
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
		{#if !chat}
			<section class="sheet empty">
				<h2 class="subtitle">{t('chat.empty.title')}</h2>
				<p class="lead">{t('chat.empty.body')}</p>
			</section>
		{:else}
			<p class="scope">
				<span class="label">{t('chat.on')}</span>
				{#each chat.bindings as b (b.kb_id)}<span class="chip">{b.kb_name ?? t('chat.deletedKb')}</span>{/each}
				<span class="small muted">{t('chat.frozen')} <Term key="revision" /></span>
			</p>
			<div class="conversation" bind:this={conversation}>
				{#if !chat.turns.length}
					<section class="sheet samples">
						<p>{t('chat.noTurns')}</p>
						<div class="row">
							{#each ['chat.sample1', 'chat.sample2', 'chat.sample3'] as const as key (key)}
								<button type="button" class="btn small" lang="vi" onclick={() => (question = t(key))}>{t(key)}</button>
							{/each}
						</div>
					</section>
				{/if}
				{#each chat.turns as turn, i (i)}
					<article class="turn">
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
								<details>
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
						<p class="pencil">{turn.mode === 'extractive' || turn.status === 'insufficient_evidence' || turn.status === 'sources_found' ? t(turn.retrieval?.mode === 'hybrid' ? 'chat.note.hybrid' : 'chat.note.lexical') : turn.note}</p>
					</article>
				{/each}
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
					<button type="submit" class="btn primary" disabled={asking || !question.trim()}><Icon name="arrow" />{t('chat.send')}</button>
				</div>
			</form>
		{/if}
	</div>
</div>

<style>
	.chat {
		display: grid;
		grid-template-columns: 300px minmax(0, 1fr);
		gap: 28px;
		align-items: start;
	}
	.setup {
		position: sticky;
		top: calc(var(--topbar) + 16px);
		display: grid;
		gap: 16px;
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
	.sessions {
		list-style: none;
		margin: 0;
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
	}
	.sessions a:hover {
		background: var(--desk);
	}
	.sessions a[aria-current='page'] {
		background: var(--desk);
		font-weight: 600;
	}
	.main {
		max-width: 900px;
		display: grid;
		gap: 18px;
	}
	.empty,
	.samples {
		padding: 28px 32px;
		display: grid;
		gap: 12px;
	}
	.scope {
		display: flex;
		gap: 8px;
		flex-wrap: wrap;
		align-items: center;
	}
	.conversation {
		display: grid;
		gap: 28px;
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
	}
	.status {
		color: var(--ink-2);
		font-weight: 500;
	}
	.statement sup {
		color: var(--focus);
		font-weight: 600;
	}
	.slip {
		margin: 0;
		padding: 16px 20px;
		display: grid;
		gap: 10px;
	}
	figcaption {
		display: flex;
		gap: 4px 10px;
		flex-wrap: wrap;
		align-items: baseline;
	}
	.cid {
		font-weight: 600;
		color: var(--focus);
	}
	blockquote {
		margin: 0;
		font-size: 17px;
		line-height: 1.8;
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
	@media (max-width: 900px) {
		.chat {
			grid-template-columns: 1fr;
		}
		.setup {
			position: static;
		}
	}
</style>
