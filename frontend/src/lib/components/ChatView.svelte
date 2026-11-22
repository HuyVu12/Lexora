<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount, tick, untrack } from 'svelte';
	import Icon from './Icon.svelte';
	import Term from './Term.svelte';
	import Skeleton from './Skeleton.svelte';
	import ConfirmDialog from './ConfirmDialog.svelte';
	import ChatSidebar from './chat/ChatSidebar.svelte';
	import ChatTurn from './chat/ChatTurn.svelte';
	import SourcePanel from './chat/SourcePanel.svelte';
	import LexoraMark from './chat/LexoraMark.svelte';
	import { api, ApiError } from '#lib/api.js';
	import { cachedAppState, loadAppState } from '#lib/app-state.svelte.js';
	import { t } from '#lib/i18n/index.svelte.js';
	import { notify, act } from '#lib/toast.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { animate, pop, popOut, reducedMotion, reveal, DUR, EASE } from '#lib/motion.js';
	import { dismiss, menuKeys, plainAnswer, finePointer, slideIn } from './chat/chat.js';
	import type { ChatSession, ChatSessionSummary, Turn } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	// The chat screen, laid out like the chat assistants people know: conversations on the left, the exchange
	// in a centred reading column, the composer pinned below it, and a citation's source on the right.
	// A conversation is bound to the revisions of its 1-5 bases when it starts (backend rule), so the scope can be
	// chosen freely before the first question and changing it later opens a new conversation.
	let { sessionId, preselect = [] }: { sessionId?: string; preselect?: string[] } = $props();

	const MAX_KBS = 5;
	const app = $derived(cachedAppState());
	let chat = $state<ChatSession | null>(null);
	let loadingChat = $state(false);
	let picked = $state<string[]>([]);
	let question = $state('');
	let mode = $state<'extractive' | 'llm'>('extractive');
	let consent = $state(false);
	let semantic = $state(true);
	let asking = $state(false);
	let pending = $state<{ question: string; sessionId: string | null } | null>(null);
	let stage = $state<'search' | 'compose'>('search');
	// Turns already there when a conversation opens appear with it; later ones reveal their parts as they arrive.
	let shownTurns = $state(Number.POSITIVE_INFINITY);
	let suggestions = $state<string[] | null>(null);
	const suggestionCache = new Map<string, string[]>();
	let scopeOpen = $state(false);
	let scopeDraft = $state<string[]>([]);
	let optionsOpen = $state(false);
	let drawerOpen = $state(false);
	let narrow = $state(false);
	let source = $state<{ turn: number; cid: string; from: HTMLElement | null } | null>(null);
	let nearBottom = $state(true);
	let scrolled = $state(false);
	let deleting = $state<ChatSessionSummary | null>(null);
	let confirmOpen = $state(false);
	let announce = $state('');

	let thread = $state<HTMLElement | null>(null);
	let column = $state<HTMLElement | null>(null);
	let composer = $state<HTMLElement | null>(null);
	let input = $state<HTMLTextAreaElement | null>(null);
	let scopeBtn = $state<HTMLButtonElement | null>(null);
	let optionsBtn = $state<HTMLButtonElement | null>(null);
	let optionsEl = $state<HTMLElement | null>(null);
	let drawerEl = $state<HTMLElement | null>(null);

	const kbs = $derived((app?.knowledge_bases ?? []).filter((k) => !k.archived_at));
	const usable = $derived(kbs.filter((k) => k.approved_claims > 0));
	const scopeIds = $derived(chat ? chat.bindings.map((b) => b.kb_id) : picked);
	const allPublic = $derived(scopeIds.length > 0 && scopeIds.every((id) => kbs.find((k) => k.id === id)?.data_class === 'public'));
	const semanticOn = $derived(!!app?.embedding_model && allPublic);
	const turns = $derived(chat?.turns ?? []);
	const pendingHere = $derived(!!pending && pending.sessionId === (chat?.id ?? null) && !(sessionId && !chat));
	const emptyThread = $derived(!loadingChat && !turns.length && !pendingHere);
	const canSend = $derived(!!question.trim() && !asking && (!!chat || picked.length > 0));
	const showLatest = $derived(!nearBottom && (turns.length > 0 || pendingHere));
	const scopeNames = $derived(chat ? chat.bindings.map((b) => b.kb_name ?? t('chat.deletedKb')) : picked.map((id) => kbs.find((k) => k.id === id)?.name ?? ''));
	const scopeChanged = $derived(scopeDraft.length !== scopeIds.length || scopeDraft.some((id) => !scopeIds.includes(id)));
	const stageText = $derived(stage === 'compose' ? t('chat.stage.compose') : t('chat.stage.search', { n: scopeIds.length }));
	const sourceCitation = $derived(source ? turns[source.turn]?.citations.find((c) => c.id === source!.cid) ?? null : null);

	onMount(() => {
		const query = window.matchMedia('(max-width: 900px)');
		const update = () => {
			narrow = query.matches;
			if (!narrow) drawerOpen = false;
		};
		update();
		query.addEventListener('change', update);
		loadAppState()
			.then(() => {
				if (!sessionId && !chat && !picked.length) picked = initialPick();
			})
			.catch((e) => notify(e.message, true));
		return () => query.removeEventListener('change', update);
	});

	// Opening a conversation (or a new one) follows the URL; the view itself stays mounted.
	$effect(() => {
		const sid = sessionId;
		void preselect.join(',');
		untrack(() => openSession(sid));
	});

	function initialPick(): string[] {
		const ids = new Set(usable.map((k) => k.id));
		const pre = preselect.filter((id) => ids.has(id));
		if (pre.length) return pre.slice(0, MAX_KBS);
		const recent = (app?.chat_sessions[0]?.bindings ?? []).map((b) => b.kb_id).filter((id) => ids.has(id));
		if (recent.length) return recent.slice(0, MAX_KBS);
		return usable.slice(0, MAX_KBS).map((k) => k.id);
	}

	function openSession(sid?: string) {
		source = null;
		scopeOpen = false;
		optionsOpen = false;
		drawerOpen = false;
		if (!sid) {
			// A new conversation keeps the scope in use unless the link names bases (?kb=...).
			const keep = picked.filter((id) => usable.some((k) => k.id === id));
			chat = null;
			loadingChat = false;
			shownTurns = 0;
			picked = preselect.length || !keep.length ? initialPick() : keep;
			tick().then(() => focusComposer());
			return;
		}
		if (chat?.id === sid) return; // Just started from this view.
		chat = null;
		loadingChat = true;
		api<ChatSession>(`/api/chat/session?id=${encodeURIComponent(sid)}`)
			.then(async (c) => {
				if (sessionId !== sid) return;
				chat = c;
				shownTurns = c.turns.length;
				picked = c.bindings.map((b) => b.kb_id);
				loadingChat = false;
				await tick();
				scrollToBottom(false);
				focusComposer();
			})
			.catch((e) => {
				if (sessionId !== sid) return;
				loadingChat = false;
				notify(e.message, true);
				if (e instanceof ApiError && e.status === 404) goto('/chat', { replace: true, reset: false });
			});
	}

	// Starter questions for the chosen bases, made offline on the server; cached per scope.
	const suggestKey = $derived(emptyThread && scopeIds.length ? scopeIds.join('|') : '');
	$effect(() => {
		const key = suggestKey;
		if (!key) return;
		const known = suggestionCache.get(key);
		suggestions = known ?? null;
		if (known) return;
		api<{ suggestions: string[] }>(`/api/chat/suggestions?${key.split('|').map((id) => `kb=${encodeURIComponent(id)}`).join('&')}`)
			.then((r) => {
				suggestionCache.set(key, r.suggestions);
				if (suggestKey === key) suggestions = r.suggestions;
			})
			.catch(() => {
				if (suggestKey === key) suggestions = [];
			});
	});

	// The composer grows with its text up to a few lines, then scrolls.
	function resize() {
		if (!input) return;
		input.style.height = 'auto';
		input.style.height = `${Math.min(input.scrollHeight, 220)}px`;
	}
	$effect(() => {
		void question;
		untrack(() => tick().then(resize));
	});

	function focusComposer(force = false) {
		if (!input || input.disabled || (!force && !finePointer())) return;
		input.focus({ preventScroll: true });
		const end = input.value.length;
		input.setSelectionRange(end, end);
	}

	function scrollToBottom(smooth: boolean) {
		if (!thread) return;
		thread.scrollTo({ top: thread.scrollHeight, behavior: smooth && !reducedMotion() ? 'smooth' : 'auto' });
	}

	/** A new answer: show it from its question when it is taller than the view, else scroll to the end. */
	function revealLatest() {
		if (!thread) return;
		const last = [...thread.querySelectorAll<HTMLElement>('.turn')].at(-1);
		if (!last) return;
		const top = thread.scrollTop + last.getBoundingClientRect().top - thread.getBoundingClientRect().top - 20;
		thread.scrollTo({ top: Math.min(top, thread.scrollHeight - thread.clientHeight), behavior: reducedMotion() ? 'auto' : 'smooth' });
	}

	function onScroll() {
		if (!thread) return;
		nearBottom = thread.scrollHeight - thread.scrollTop - thread.clientHeight < 96;
		scrolled = thread.scrollTop > 4;
	}

	// Content that changes height without a scroll (the source panel narrowing the column) re-measures too.
	$effect(() => {
		if (!column || !thread) return;
		const observer = new ResizeObserver(() => onScroll());
		observer.observe(column);
		observer.observe(thread); // The composer growing or a wrapped disclaimer changes the view's height.
		return () => observer.disconnect();
	});

	function statusText(turn: Turn | undefined): string {
		if (!turn) return '';
		if (turn.status === 'sources_found') return t('chat.found', { n: turn.citations.length });
		if (turn.status === 'insufficient_evidence') return t('chat.noEvidence.title');
		return t(`chat.status.${turn.status}` as MessageKey);
	}

	async function send() {
		const text = question.trim();
		if (!text || asking) return;
		if (!chat && !picked.length) {
			openScope();
			notify({ key: 'chat.pickOne' }, true);
			return;
		}
		asking = true;
		stage = 'search';
		pending = { question: text, sessionId: chat?.id ?? null };
		question = '';
		const llm = mode === 'llm';
		// The second stage is real only for the model path: retrieval is quick, writing and checking is not.
		const timer = llm ? setTimeout(() => (stage = 'compose'), 900) : undefined;
		await tick();
		scrollToBottom(true);
		let target = chat;
		try {
			if (!target) {
				target = await api<ChatSession>('/api/chat/start', { kb_ids: picked });
				chat = target;
				shownTurns = 0;
				pending = { question: text, sessionId: target.id };
				goto(`/chat/${target.id}`, { reset: false });
			}
			const id = target.id;
			await api('/api/chat/ask', { session_id: id, question: text, mode, allow_public_transfer: llm && consent, semantic: semanticOn && semantic });
			const [next] = await Promise.all([api<ChatSession>(`/api/chat/session?id=${encodeURIComponent(id)}`), loadAppState()]);
			if (chat?.id === id) {
				const follow = nearBottom;
				chat = next;
				announce = `${t('chat.answerReady')} ${statusText(next.turns.at(-1))}`;
				await tick();
				if (follow) revealLatest();
			}
		} catch (e) {
			notify(e instanceof Error ? e.message : String(e), true);
			if (!question.trim()) question = text; // Nothing typed is lost.
		} finally {
			clearTimeout(timer);
			pending = null;
			asking = false;
		}
	}

	function onKey(event: KeyboardEvent) {
		// Enter sends, Shift+Enter breaks the line; never while an input method (Telex, VNI) is composing a letter.
		if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && event.keyCode !== 229) {
			event.preventDefault();
			send();
		}
	}

	function fill(text: string) {
		question = text;
		tick().then(() => focusComposer(true));
	}

	async function copy(turn: Turn): Promise<boolean> {
		try {
			await navigator.clipboard.writeText(plainAnswer(turn));
			announce = t('chat.copied');
			return true;
		} catch {
			notify({ key: 'chat.copyFailed' }, true);
			return false;
		}
	}

	/** The reading column and composer glide to their new centre when the source panel opens or closes. */
	async function shift(change: () => void) {
		const elements = [column, composer].filter((e): e is HTMLElement => !!e);
		const before = elements.map((e) => e.getBoundingClientRect().left);
		change();
		await tick();
		elements.forEach((e, i) => {
			const dx = before[i] - e.getBoundingClientRect().left;
			if (Math.abs(dx) > 1) animate(e, { transform: [`translateX(${dx}px)`, 'none'], duration: DUR.slow, ease: EASE.out });
		});
	}

	function cite(turn: number, cid: string, from: HTMLElement) {
		if (source && source.turn === turn && source.cid === cid) return closeSource();
		if (source) source = { turn, cid, from };
		else shift(() => (source = { turn, cid, from }));
	}

	function closeSource() {
		const from = source?.from;
		shift(() => (source = null));
		if (from?.isConnected) from.focus({ preventScroll: true });
	}

	function openScope() {
		optionsOpen = false;
		scopeDraft = [...scopeIds];
		scopeOpen = true;
		tick().then(() => document.querySelector<HTMLInputElement>('.scope-pop input:not([disabled])')?.focus());
	}

	function closeScope(refocus = true) {
		scopeOpen = false;
		if (refocus) scopeBtn?.focus();
	}

	function toggleKb(id: string, on: boolean) {
		const next = on ? [...scopeDraft, id].slice(0, MAX_KBS) : scopeDraft.filter((x) => x !== id);
		scopeDraft = next;
		if (!chat) picked = next; // Before the first question the scope applies at once.
	}

	/** Inside a conversation the bases are fixed: a different scope continues in a new conversation. */
	async function applyScope() {
		if (!scopeDraft.length) return;
		picked = [...scopeDraft];
		closeScope(false);
		await goto('/chat', { reset: false });
		notify({ key: 'chat.scope.moved', params: { n: picked.length } });
	}

	function toggleOptions() {
		scopeOpen = false;
		optionsOpen = !optionsOpen;
		if (optionsOpen) tick().then(() => optionsEl?.querySelector<HTMLInputElement>('input:checked, input:not([disabled])')?.focus());
	}

	function closeOptions(refocus = true) {
		optionsOpen = false;
		if (refocus) optionsBtn?.focus();
	}

	function newChat() {
		drawerOpen = false;
		if (!sessionId) {
			// Already on a new conversation: start over from an empty composer.
			question = '';
			focusComposer(true);
			return;
		}
		goto('/chat', { reset: false });
	}

	async function rename(id: string, title: string): Promise<boolean> {
		return act(async () => {
			const result = await api<{ id: string; title: string | null; custom_title: boolean }>('/api/chat/rename', { session_id: id, title });
			const row = app?.chat_sessions.find((s) => s.id === id);
			if (row) Object.assign(row, { title: result.title, custom_title: result.custom_title });
			if (chat?.id === id) Object.assign(chat, { title: result.title, custom_title: result.custom_title });
			announce = t('chat.renamed');
			loadAppState().catch(() => undefined);
		});
	}

	function askDelete(s: ChatSessionSummary) {
		deleting = s;
		confirmOpen = true;
	}

	async function confirmDelete() {
		const target = deleting;
		if (!target) return;
		await act(async () => {
			await api('/api/chat/hide', { session_id: target.id });
			if (app) app.chat_sessions = app.chat_sessions.filter((s) => s.id !== target.id);
			notify({ key: 'chat.deleted' });
			if (chat?.id === target.id) await goto('/chat', { reset: false });
			loadAppState().catch(() => undefined);
		});
	}

	$effect(() => {
		if (!drawerOpen) return;
		tick().then(() => drawerEl?.querySelector<HTMLElement>('.new')?.focus());
	});

	function onWindowKey(event: KeyboardEvent) {
		if (event.key !== 'Escape' || event.defaultPrevented) return;
		if (drawerOpen) drawerOpen = false;
		else if (source && !confirmOpen) closeSource();
	}
</script>

<svelte:head><title>{chat?.title ?? t('chat.title')} · Lexora</title></svelte:head>
<svelte:window onkeydown={onWindowKey} />

<div class="chat-shell" class:with-source={!!source && !!sourceCitation && !!chat}>
	<h1 class="visually-hidden">{t('chat.title')}</h1>
	{#if narrow && drawerOpen}
		<button type="button" class="drawer-backdrop" tabindex="-1" aria-label={t('chat.closeSidebar')} onclick={() => (drawerOpen = false)} transition:slideIn={{ duration: DUR.base }}></button>
	{/if}
	<div class="sidebar" id="chat-sidebar" class:open={drawerOpen} bind:this={drawerEl} inert={narrow && !drawerOpen}>
		<ChatSidebar
			sessions={app ? app.chat_sessions : null}
			currentId={chat?.id ?? sessionId}
			onnew={newChat}
			onrename={rename}
			ondelete={askDelete}
			onnavigate={() => (drawerOpen = false)}
		/>
	</div>

	<div class="main" inert={narrow && drawerOpen}>
		<header class="bar" class:scrolled>
			<button type="button" class="icon-btn narrow-only" aria-label={t('chat.openSidebar')} aria-expanded={drawerOpen} aria-controls="chat-sidebar" onclick={() => (drawerOpen = true)}><Icon name="menu" size={20} /></button>
			<div class="bar-text">
				{#if loadingChat}
					<Skeleton width="220px" height="15px" />
				{:else}
					<h2 class="bar-title">{chat?.title ?? (pendingHere && pending ? pending.question : chat ? t('chat.untitled') : t('chat.new'))}</h2>
				{/if}
				{#if chat}
					<p class="bar-scope"><span class="scope-names">{scopeNames.join(', ')}</span><span class="dot" aria-hidden="true"></span><Term key="revision">{t('chat.frozen')}</Term></p>
				{/if}
			</div>
			<button type="button" class="icon-btn narrow-only" aria-label={t('chat.new')} onclick={newChat} data-tour="chat-new"><Icon name="plus" size={20} /></button>
		</header>

		<div class="thread" bind:this={thread} onscroll={onScroll}>
			<div class="column" bind:this={column}>
				{#if loadingChat}
					<div class="ghost-thread" aria-busy="true">
						<span class="visually-hidden" role="status">{t('common.loading')}</span>
						{#each [0, 1] as i (i)}
							<div class="ghost-q"><Skeleton width="{46 - i * 10}%" height="40px" radius="18px" /></div>
							<div class="ghost-a"><Skeleton width="26px" height="26px" radius="7px" /><div class="ghost-lines"><Skeleton lines={3} height="14px" gap="11px" last="62%" /></div></div>
						{/each}
					</div>
				{:else if emptyThread}
					<section class="welcome" aria-labelledby="chat-welcome">
						<LexoraMark size={40} />
						<h2 class="welcome-title" id="chat-welcome">{t('chat.empty.title')}</h2>
						<p class="welcome-body">{t('chat.empty.body')}</p>
						{#if app && !usable.length}
							<p class="welcome-none">{t('chat.noKb')}</p>
							{#if canReview(session.account)}<a class="btn" href="/import"><Icon name="upload" />{t('chat.noKb.action')}</a>{/if}
						{:else}
							<div class="suggest" aria-label={t('chat.suggest.label')} role="group">
								{#if suggestions === null}
									{#each [0, 1, 2, 3] as i (i)}<div class="suggestion ghost" aria-hidden="true"><Skeleton width="{82 - i * 9}%" height="14px" /><Skeleton width="40%" height="14px" /></div>{/each}
								{:else}
									{#each suggestions as text, i (text)}
										<button type="button" class="suggestion" lang="vi" aria-label={t('chat.suggest.fill', { q: text })} onclick={() => fill(text)} {@attach reveal({ y: 6, delay: i * 45 })}>
											<span>{text}</span>
											<Icon name="arrow" size={16} />
										</button>
									{/each}
								{/if}
							</div>
						{/if}
					</section>
				{:else}
					{#each turns as turn, i (turn.id ?? i)}
						<ChatTurn
							{turn}
							index={i}
							fresh={i >= shownTurns}
							active={source ? `${source.turn}:${source.cid}` : null}
							kbCount={scopeIds.length}
							oncite={cite}
							onedit={fill}
							oncopy={copy}
						/>
					{/each}
					{#if pendingHere && pending}
						<ChatTurn
							turn={{ question: pending.question, status: 'pending', statements: [], citations: [], note: '' }}
							index={turns.length}
							kbCount={scopeIds.length}
							stage={stageText}
							oncite={cite}
							onedit={fill}
							oncopy={copy}
						/>
					{/if}
				{/if}
			</div>
		</div>

		<div class="composer-wrap">
			{#if showLatest}
				<button type="button" class="latest" onclick={() => scrollToBottom(true)} in:pop={{ origin: 'bottom center', y: 4 }} out:popOut={{ y: 4 }}><Icon name="down" size={16} />{t('chat.latest')}</button>
			{/if}
			<form class="composer" bind:this={composer} onsubmit={(e) => { e.preventDefault(); send(); }}>
				{#if mode === 'llm'}
					<label class="consent"><input type="checkbox" bind:checked={consent} />{t('chat.consent')}</label>
				{/if}
				<label class="visually-hidden" for="chat-input">{t('chat.question')}</label>
				<textarea
					id="chat-input"
					data-tour="chat-composer"
					rows="1"
					maxlength="1500"
					placeholder={t('chat.placeholder')}
					bind:this={input}
					bind:value={question}
					oninput={resize}
					onkeydown={onKey}
					disabled={!!app && !usable.length && !chat}
				></textarea>
				<div class="tools">
					<div class="anchor">
						<button type="button" class="pill" data-tour="chat-scope" bind:this={scopeBtn} aria-haspopup="dialog" aria-expanded={scopeOpen} aria-controls="chat-scope" onclick={() => (scopeOpen ? closeScope() : openScope())} disabled={!app}>
							<Icon name="book" size={16} />
							<span>{scopeIds.length ? t('chat.scope.pill', { n: scopeIds.length }) : t('chat.scope.none')}</span>
							<Icon name="chevron" size={14} />
						</button>
						{#if scopeOpen}
							<div class="pop scope-pop" id="chat-scope" data-tour-part="chat-scope" role="dialog" aria-labelledby="chat-scope-title" in:pop={{ origin: 'bottom left', y: 6 }} out:popOut={{ y: 4 }} {@attach dismiss(() => closeScope(), () => scopeBtn)}>
								<p class="pop-title" id="chat-scope-title">{t('chat.scope.title')}</p>
								<p class="pop-hint">{chat ? t('chat.scope.locked') : t('chat.scope.hint')}</p>
								{#if !kbs.length}
									<p class="pop-hint">{t('chat.noKb')}</p>
								{:else}
									<div class="kb-list">
										{#each kbs as kb (kb.id)}
											{@const on = scopeDraft.includes(kb.id)}
											<label class="kb-option" class:off={!kb.approved_claims}>
												<input type="checkbox" checked={on} disabled={!kb.approved_claims || (!on && scopeDraft.length >= MAX_KBS)} onchange={(e) => toggleKb(kb.id, e.currentTarget.checked)} />
												<span class="kb-text">
													<span class="kb-name">{kb.name}</span>
													<span class="kb-meta">{kb.approved_claims ? t('chat.norms', { n: kb.approved_claims }) : t('chat.normsNone')} · {kb.data_class === 'private' ? t('kb.private') : t('kb.public')}</span>
												</span>
											</label>
										{/each}
									</div>
									<p class="pop-hint">{t('chat.scope.max', { n: MAX_KBS })}</p>
								{/if}
								{#if chat}
									<div class="pop-foot">
										<button type="button" class="btn small quiet" onclick={() => closeScope()}>{t('common.cancel')}</button>
										<button type="button" class="btn small primary" disabled={!scopeChanged || !scopeDraft.length} onclick={applyScope}><Icon name="plus" />{t('chat.scope.apply', { n: scopeDraft.length })}</button>
									</div>
								{/if}
							</div>
						{/if}
					</div>
					<div class="anchor">
						<button type="button" class="pill" data-tour="chat-options" bind:this={optionsBtn} aria-haspopup="dialog" aria-expanded={optionsOpen} aria-controls="chat-options" onclick={toggleOptions}>
							<Icon name="sliders" size={16} />
							<span class="pill-label">{mode === 'llm' ? t('chat.mode.short.llm') : t('chat.mode.short.extractive')}</span>
							<Icon name="chevron" size={14} />
						</button>
						{#if optionsOpen}
							<div class="pop options-pop" id="chat-options" data-tour-part="chat-options" role="dialog" tabindex="-1" aria-labelledby="chat-options-title" bind:this={optionsEl} in:pop={{ origin: 'bottom left', y: 6 }} out:popOut={{ y: 4 }} onkeydown={(e) => menuKeys(e, optionsEl)} {@attach dismiss(() => closeOptions(), () => optionsBtn)}>
								<fieldset>
									<legend class="pop-title" id="chat-options-title">{t('chat.mode')}</legend>
									<label class="choice-row">
										<input type="radio" name="chat-mode" value="extractive" bind:group={mode} />
										<span><strong>{t('chat.mode.short.extractive')}</strong><span>{t('chat.mode.extractive')}</span></span>
									</label>
									{#if app?.router_enabled}
										<label class="choice-row">
											<input type="radio" name="chat-mode" value="llm" bind:group={mode} />
											<span><strong>{t('chat.mode.short.llm')}</strong><span>{t('chat.mode.llm.d')}</span></span>
										</label>
									{/if}
								</fieldset>
								{#if app?.embedding_model}
									<fieldset>
										<legend class="pop-title">{t('chat.search')}</legend>
										<label class="choice-row">
											<input type="checkbox" bind:checked={semantic} disabled={!semanticOn} />
											<span><span>{allPublic ? t('chat.semantic', { model: app.embedding_model }) : t('chat.semanticPrivate')}</span></span>
										</label>
									</fieldset>
								{/if}
							</div>
						{/if}
					</div>
					<button type="submit" class="send" data-tour="chat-send" disabled={!canSend} aria-label={t('chat.send')} title={t('chat.send')}>
						{#if asking}<span class="spinner" aria-hidden="true"></span>{:else}<Icon name="send" size={18} />{/if}
					</button>
				</div>
			</form>
			<p class="disclaimer">{t('chat.disclaimer')}</p>
		</div>
		<p class="visually-hidden" aria-live="polite">{announce}</p>
	</div>

	{#if source && sourceCitation && chat}
		<SourcePanel sessionId={chat.id} turn={source.turn} citation={sourceCitation} number={turns[source.turn].citations.indexOf(sourceCitation) + 1} onclose={closeSource} />
	{/if}
</div>

<ConfirmDialog bind:open={confirmOpen} title={t('chat.delete.title')} confirmLabel={t('chat.delete')} tone="danger" onconfirm={confirmDelete}>
	<p class="confirm-body">{t('chat.delete.body', { title: deleting?.title ?? t('chat.untitled') })}</p>
</ConfirmDialog>

<style>
	/* The chat fills the window under the top bar; only the thread and the lists scroll. */
	:global(html:has(.chat-shell)) {
		background: var(--paper);
	}
	:global(body:has(.chat-shell)) {
		overflow: hidden;
	}
	.chat-shell {
		display: grid;
		grid-template-columns: 272px minmax(0, 1fr);
		height: calc(100dvh - var(--topbar));
		overflow: hidden;
	}
	.chat-shell.with-source {
		grid-template-columns: 272px minmax(0, 1fr) clamp(360px, 30vw, 440px);
	}
	.sidebar {
		min-height: 0;
		background: var(--desk);
		border-right: 1px solid var(--rule);
	}
	.main {
		position: relative;
		display: flex;
		flex-direction: column;
		min-width: 0;
		min-height: 0;
		background: var(--paper);
	}
	.bar {
		display: flex;
		align-items: center;
		gap: 8px;
		min-height: 52px;
		padding: 8px 24px;
		border-bottom: 1px solid transparent;
		transition: border-color var(--dur-fast) ease;
	}
	.bar.scrolled {
		border-bottom-color: var(--rule);
	}
	.bar-text {
		flex: 1;
		min-width: 0;
		display: grid;
		gap: 1px;
	}
	.bar-title {
		font: 600 15px/1.35 var(--sans);
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}
	.bar-scope {
		display: flex;
		align-items: center;
		min-width: 0;
		font-size: 12.5px;
		color: var(--muted);
		white-space: nowrap;
	}
	.scope-names {
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.dot {
		flex: none;
		width: 3px;
		height: 3px;
		margin: 0 8px;
		border-radius: 50%;
		background: var(--rule-strong);
	}
	.icon-btn {
		display: grid;
		place-items: center;
		flex: none;
		width: 36px;
		height: 36px;
		padding: 0;
		border: 0;
		border-radius: var(--r-control);
		background: transparent;
		color: var(--ink-2);
		cursor: pointer;
	}
	.icon-btn:hover {
		background: var(--desk);
	}
	.narrow-only {
		display: none;
	}
	.thread {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		overscroll-behavior: contain;
	}
	.column {
		display: grid;
		gap: 40px;
		max-width: 768px;
		margin: 0 auto;
		padding: 20px 32px 40px;
	}
	.welcome {
		display: grid;
		justify-items: center;
		gap: 10px;
		padding: clamp(24px, 9vh, 96px) 0 8px;
		text-align: center;
	}
	.welcome-title {
		margin-top: 8px;
		font: 600 24px/1.25 var(--serif);
		letter-spacing: -0.01em;
	}
	.welcome-body {
		max-width: 52ch;
		color: var(--ink-2);
		line-height: 1.6;
	}
	.welcome-none {
		margin-top: 10px;
		color: var(--muted);
	}
	.suggest {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 10px;
		width: 100%;
		margin-top: 22px;
		text-align: left;
	}
	.suggestion {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 12px;
		min-height: 64px;
		padding: 12px 14px;
		border: 1px solid var(--rule);
		border-radius: 12px;
		background: var(--paper);
		color: var(--ink);
		font-size: 14.5px;
		line-height: 1.45;
		text-align: left;
		cursor: pointer;
		transition:
			border-color var(--dur-fast) ease,
			background-color var(--dur-fast) ease,
			transform var(--dur-fast) var(--ease-out);
	}
	.suggestion :global(svg) {
		flex: none;
		margin-top: 2px;
		color: var(--muted);
		transition:
			transform var(--dur-base) var(--ease-out),
			color var(--dur-fast) ease;
	}
	@media (hover: hover) {
		.suggestion:hover:not(.ghost) {
			border-color: var(--rule-strong);
			background: #fafbfa;
		}
		.suggestion:hover:not(.ghost) :global(svg) {
			color: var(--ink);
			transform: translateX(2px);
		}
	}
	.suggestion:active:not(.ghost) {
		transform: scale(0.985);
	}
	.suggestion.ghost {
		flex-direction: column;
		gap: 8px;
		cursor: default;
	}
	.ghost-thread {
		display: grid;
		gap: 22px;
	}
	.ghost-q {
		display: flex;
		justify-content: flex-end;
	}
	.ghost-a {
		display: grid;
		grid-template-columns: 26px minmax(0, 1fr);
		gap: 14px;
		margin-bottom: 18px;
	}
	.ghost-lines {
		padding-top: 4px;
	}
	/* Composer: pinned under the thread at the same reading width, with a soft fade above it. */
	.composer-wrap {
		position: relative;
		width: 100%;
		max-width: 768px;
		margin: 0 auto;
		padding: 0 32px 10px;
	}
	.composer-wrap::before {
		content: '';
		position: absolute;
		left: 0;
		right: 0;
		bottom: 100%;
		height: 28px;
		background: linear-gradient(rgb(255 255 255 / 0), var(--paper));
		pointer-events: none;
	}
	.composer {
		display: grid;
		gap: 4px;
		padding: 10px 10px 8px 16px;
		border: 1px solid var(--rule-strong);
		border-radius: 18px;
		background: var(--paper);
		box-shadow: 0 1px 2px rgb(20 22 24 / 0.05), 0 6px 20px rgb(20 22 24 / 0.07);
		transition:
			border-color var(--dur-fast) ease,
			box-shadow var(--dur-fast) ease;
	}
	.composer:focus-within {
		border-color: var(--ink-2);
		box-shadow: 0 1px 2px rgb(20 22 24 / 0.06), 0 8px 26px rgb(20 22 24 / 0.1);
	}
	.composer textarea {
		display: block;
		width: 100%;
		min-height: 28px;
		max-height: 220px;
		margin: 2px 0 0;
		padding: 4px 6px 4px 0;
		border: 0;
		outline: none;
		background: transparent;
		resize: none;
		font-size: 15.5px;
		line-height: 1.55;
	}
	.composer textarea::placeholder {
		color: #7a7f84;
	}
	.composer textarea:disabled {
		cursor: not-allowed;
	}
	.consent {
		display: flex;
		align-items: flex-start;
		gap: 8px;
		margin: 0 0 4px;
		padding: 7px 10px;
		border-radius: 10px;
		background: var(--attention-soft);
		color: var(--ink);
		font-size: 13px;
		line-height: 1.45;
	}
	.consent input {
		margin-top: 2px;
		flex: none;
	}
	.tools {
		display: flex;
		align-items: center;
		gap: 6px;
		margin-left: -6px;
	}
	.anchor {
		position: relative;
		flex: 0 1 auto;
		min-width: 0;
	}
	.pill {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		max-width: 100%;
		min-height: 32px;
		padding: 4px 10px;
		border: 1px solid var(--rule);
		border-radius: 999px;
		background: var(--paper);
		color: var(--ink-2);
		font-size: 13px;
		font-weight: 500;
		white-space: nowrap;
		cursor: pointer;
		transition:
			background-color var(--dur-fast) ease,
			border-color var(--dur-fast) ease;
	}
	.pill span {
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.pill :global(svg) {
		flex: none;
	}
	.pill:hover:not(:disabled),
	.pill[aria-expanded='true'] {
		background: var(--desk);
		border-color: var(--rule-strong);
	}
	.pill:disabled {
		opacity: 0.6;
		cursor: default;
	}
	.send {
		display: grid;
		place-items: center;
		flex: none;
		width: 36px;
		height: 36px;
		margin-left: auto;
		padding: 0;
		border: 0;
		border-radius: 50%;
		background: var(--graphite);
		color: #fff;
		cursor: pointer;
		transition:
			background-color var(--dur-fast) ease,
			opacity var(--dur-fast) ease,
			transform var(--dur-fast) var(--ease-out);
	}
	.send:hover:not(:disabled) {
		background: var(--graphite-hover);
	}
	.send:active:not(:disabled) {
		transform: scale(0.92);
	}
	.send:disabled {
		background: var(--rule-strong);
		cursor: not-allowed;
	}
	.send:has(.spinner):disabled {
		background: var(--graphite);
	}
	.spinner {
		width: 16px;
		height: 16px;
		border: 2px solid rgb(255 255 255 / 0.35);
		border-top-color: #fff;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
	.disclaimer {
		margin-top: 8px;
		font-size: 12px;
		line-height: 1.45;
		color: var(--muted);
		text-align: center;
		text-wrap: balance;
	}
	.latest {
		position: absolute;
		bottom: calc(100% + 10px);
		left: 50%;
		z-index: 2;
		display: inline-flex;
		align-items: center;
		gap: 6px;
		translate: -50% 0;
		padding: 6px 12px 6px 10px;
		border: 1px solid var(--rule);
		border-radius: 999px;
		background: var(--paper);
		color: var(--ink-2);
		font-size: 13px;
		font-weight: 500;
		box-shadow: var(--shadow-sheet);
		cursor: pointer;
	}
	.latest:hover {
		color: var(--ink);
		border-color: var(--rule-strong);
	}
	/* Popovers open upwards from the composer. */
	.pop {
		position: absolute;
		bottom: calc(100% + 8px);
		left: 0;
		z-index: 30;
		display: grid;
		gap: 10px;
		width: min(380px, calc(100vw - 32px));
		max-height: min(60dvh, 460px);
		overflow-y: auto;
		padding: 14px;
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: 12px;
		box-shadow: var(--shadow-pop);
	}
	.pop-title {
		padding: 0;
		font: 600 14px/1.4 var(--sans);
		color: var(--ink);
	}
	.pop-hint {
		margin-top: -4px;
		font-size: 12.5px;
		line-height: 1.5;
		color: var(--muted);
	}
	.kb-list {
		display: grid;
		gap: 2px;
		margin: 0 -6px;
	}
	.kb-option {
		display: grid;
		grid-template-columns: 18px minmax(0, 1fr);
		gap: 10px;
		align-items: start;
		padding: 8px 8px;
		border-radius: 8px;
		cursor: pointer;
		transition: background-color var(--dur-fast) ease;
	}
	.kb-option:hover:not(.off) {
		background: var(--desk);
	}
	.kb-option.off {
		cursor: default;
		opacity: 0.6;
	}
	.kb-option input {
		margin: 3px 0 0;
	}
	.kb-text {
		display: grid;
		gap: 1px;
		min-width: 0;
	}
	.kb-name {
		font-size: 14px;
		font-weight: 500;
		line-height: 1.4;
		overflow-wrap: anywhere;
	}
	.kb-meta {
		font-size: 12.5px;
		color: var(--muted);
	}
	.pop-foot {
		display: flex;
		justify-content: flex-end;
		gap: 8px;
		padding-top: 10px;
		border-top: 1px solid var(--rule);
	}
	fieldset {
		display: grid;
		gap: 2px;
		margin: 0;
		padding: 0;
		border: 0;
	}
	fieldset + fieldset {
		padding-top: 10px;
		border-top: 1px solid var(--rule);
	}
	legend {
		margin-bottom: 4px;
	}
	.choice-row {
		display: grid;
		grid-template-columns: 18px minmax(0, 1fr);
		gap: 10px;
		align-items: start;
		margin: 0 -6px;
		padding: 8px;
		border-radius: 8px;
		cursor: pointer;
		transition: background-color var(--dur-fast) ease;
	}
	.choice-row:hover {
		background: var(--desk);
	}
	.choice-row input {
		margin: 3px 0 0;
	}
	.choice-row > span {
		display: grid;
		gap: 1px;
		font-size: 13px;
		line-height: 1.45;
		color: var(--muted);
	}
	.choice-row strong {
		font-size: 14px;
		font-weight: 500;
		color: var(--ink);
	}
	.confirm-body {
		margin: 10px 0 4px;
		color: var(--ink-2);
		line-height: 1.55;
	}
	.drawer-backdrop {
		display: none;
	}
	@media (max-width: 1100px) {
		.chat-shell.with-source {
			grid-template-columns: 240px minmax(0, 1fr) 360px;
		}
		.chat-shell {
			grid-template-columns: 240px minmax(0, 1fr);
		}
	}
	/* Phone and narrow tablet: the list becomes an off-canvas drawer, the source a bottom sheet. */
	@media (max-width: 900px) {
		.chat-shell,
		.chat-shell.with-source {
			grid-template-columns: minmax(0, 1fr);
		}
		.sidebar {
			position: fixed;
			top: 0;
			bottom: 0;
			left: 0;
			z-index: 71;
			width: min(86vw, 320px);
			border-right: 0;
			box-shadow: var(--shadow-pop);
			transform: translateX(-104%);
			visibility: hidden;
			transition:
				transform var(--dur-slow) var(--ease-drawer),
				visibility 0s linear var(--dur-slow);
		}
		.sidebar.open {
			transform: none;
			visibility: visible;
			transition:
				transform var(--dur-slow) var(--ease-drawer),
				visibility 0s;
		}
		.drawer-backdrop {
			display: block;
			position: fixed;
			inset: 0;
			z-index: 70;
			padding: 0;
			border: 0;
			background: rgb(20 22 24 / 0.32);
			cursor: default;
		}
		.narrow-only {
			display: grid;
		}
		.bar {
			padding: 6px 8px;
			border-bottom-color: var(--rule);
		}
		.bar-text {
			text-align: center;
		}
		.bar-scope {
			justify-content: center;
		}
		.column {
			gap: 32px;
			padding: 18px 16px 32px;
		}
		.composer-wrap {
			padding: 0 12px calc(8px + env(safe-area-inset-bottom));
		}
		.suggest {
			grid-template-columns: minmax(0, 1fr);
			margin-top: 16px;
		}
		.suggestion {
			min-height: 0;
		}
		.welcome {
			padding-top: 20px;
		}
		/* Popovers span the composer's width, so neither runs off a narrow screen. */
		.tools {
			position: relative;
		}
		.anchor {
			position: static;
		}
		.pop {
			left: 6px;
			right: 0;
			width: auto;
		}
	}
	/* Phone: the options pill keeps its icon only, so both pills and the send button fit on one row. */
	@media (max-width: 480px) {
		.pill-label {
			position: absolute;
			width: 1px;
			height: 1px;
			overflow: hidden;
			clip-path: inset(50%);
			white-space: nowrap;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.spinner {
			animation-duration: 2s;
		}
	}
</style>
