<script lang="ts">
	import { tick } from 'svelte';
	import { flip } from 'svelte/animate';
	import Icon from '../Icon.svelte';
	import Skeleton from '../Skeleton.svelte';
	import { t } from '#lib/i18n/index.svelte.js';
	import { pop, popOut, DUR } from '#lib/motion.js';
	import { GROUPS, groupOf, dismiss, menuKeys, type Group } from './chat.js';
	import type { ChatSessionSummary } from '#lib/types.js';

	// The conversation list: a prominent "new conversation" button, then the account's own conversations grouped
	// by their last question (today, the previous seven days, older). Each row has a menu to rename or delete it.
	let {
		sessions,
		currentId,
		onnew,
		onrename,
		ondelete,
		onnavigate
	}: {
		sessions: ChatSessionSummary[] | null;
		currentId?: string;
		onnew: () => void;
		onrename: (id: string, title: string) => Promise<boolean>;
		ondelete: (session: ChatSessionSummary) => void;
		onnavigate?: () => void;
	} = $props();

	const grouped = $derived.by(() => {
		const now = new Date();
		const by: Record<Group, ChatSessionSummary[]> = { today: [], week: [], older: [] };
		for (const s of sessions ?? []) by[groupOf(s.updated_at ?? s.created_at, now)].push(s);
		return GROUPS.filter((g) => by[g].length).map((g) => ({ group: g, rows: by[g] }));
	});

	let menuFor = $state<string | null>(null);
	let menuEl = $state<HTMLElement | null>(null);
	// The menu is placed in the viewport beside its button, so the scrolling list never clips it.
	let menuPos = $state({ top: 0, left: 0 });
	let editing = $state<string | null>(null);
	let draft = $state('');
	let saving = false;

	const label = (s: ChatSessionSummary) => s.title ?? t('chat.untitled');
	const trigger = (id: string) => document.getElementById(`chat-row-menu-${id}`);

	async function openMenu(id: string) {
		menuFor = menuFor === id ? null : id;
		const box = trigger(id)?.getBoundingClientRect();
		if (menuFor && box) {
			const height = 92;
			const below = box.bottom + 4 + height < window.innerHeight;
			menuPos = { top: below ? box.bottom + 4 : box.top - height - 4, left: Math.max(8, box.right - 172) };
			await tick();
			menuEl?.querySelector<HTMLElement>('[role="menuitem"]')?.focus();
		}
	}

	function closeMenu(refocus = true) {
		const id = menuFor;
		menuFor = null;
		if (refocus && id) trigger(id)?.focus();
	}

	async function startRename(s: ChatSessionSummary) {
		closeMenu(false);
		editing = s.id;
		draft = s.title ?? '';
		await tick();
		const input = document.getElementById(`chat-rename-${s.id}`) as HTMLInputElement | null;
		input?.focus();
		input?.select();
	}

	async function commit(s: ChatSessionSummary) {
		if (saving || editing !== s.id) return;
		const value = draft.trim();
		if (value === (s.title ?? '').trim()) {
			editing = null;
			return;
		}
		saving = true;
		const ok = await onrename(s.id, value);
		saving = false;
		if (ok) {
			editing = null;
			await tick();
			trigger(s.id)?.focus();
		}
	}

	function cancel(s: ChatSessionSummary) {
		editing = null;
		tick().then(() => trigger(s.id)?.focus());
	}
</script>

<div class="side">
	<button type="button" class="btn primary new" onclick={onnew}><Icon name="plus" />{t('chat.new')}</button>
	<nav class="list" aria-label={t('chat.sidebar')} onscroll={() => menuFor && closeMenu(false)}>
		{#if sessions === null}
			<div class="ghost" aria-hidden="true">
				<Skeleton width="56px" height="11px" />
				{#each [0, 1, 2, 3] as i (i)}<Skeleton width="{88 - i * 11}%" height="14px" />{/each}
			</div>
		{:else if !sessions.length}
			<p class="empty small">{t('chat.sidebar.empty')}</p>
		{:else}
			{#each grouped as { group, rows } (group)}
				<section class="group" aria-labelledby="chat-group-{group}">
					<h2 class="group-name" id="chat-group-{group}">{t(`chat.group.${group}`)}</h2>
					<ul>
						{#each rows as s (s.id)}
							<li class="row" class:current={s.id === currentId} class:menu-open={menuFor === s.id} animate:flip={{ duration: DUR.base }}>
								{#if editing === s.id}
									<label class="rename">
										<span class="visually-hidden">{t('chat.rename.label')}</span>
										<input
											id="chat-rename-{s.id}"
											class="input"
											maxlength="120"
											bind:value={draft}
											placeholder={t('chat.untitled')}
											onblur={() => commit(s)}
											onkeydown={(e) => {
												if (e.key === 'Enter' && !e.isComposing) {
													e.preventDefault();
													commit(s);
												} else if (e.key === 'Escape') {
													e.preventDefault();
													cancel(s);
												}
											}}
										/>
									</label>
								{:else}
									<a href="/chat/{s.id}" class:untitled={!s.title} aria-current={s.id === currentId ? 'page' : undefined} title={label(s)} onclick={() => onnavigate?.()}>
										<span class="name">{label(s)}</span>
									</a>
									<button
										type="button"
										class="more"
										id="chat-row-menu-{s.id}"
										aria-label={t('chat.row.menu', { title: label(s) })}
										aria-haspopup="menu"
										aria-expanded={menuFor === s.id}
										onclick={() => openMenu(s.id)}><Icon name="more" size={18} /></button
									>
									{#if menuFor === s.id}
										<div
											class="menu"
											role="menu"
											tabindex="-1"
											aria-label={t('chat.row.menu', { title: label(s) })}
											bind:this={menuEl}
											style:top="{menuPos.top}px"
											style:left="{menuPos.left}px"
											in:pop={{ origin: 'top right' }}
											out:popOut
											onkeydown={(e) => menuKeys(e, menuEl)}
											{@attach dismiss(() => closeMenu(), () => trigger(s.id))}
										>
											<button type="button" role="menuitem" onclick={() => startRename(s)}><Icon name="edit" size={16} />{t('chat.rename')}</button>
											<button type="button" role="menuitem" class="danger" onclick={() => { closeMenu(false); ondelete(s); }}><Icon name="x" size={16} />{t('chat.delete')}</button>
										</div>
									{/if}
								{/if}
							</li>
						{/each}
					</ul>
				</section>
			{/each}
		{/if}
	</nav>
</div>

<style>
	.side {
		display: flex;
		flex-direction: column;
		gap: 14px;
		height: 100%;
		min-height: 0;
		padding: 14px 10px;
	}
	.new {
		width: 100%;
		justify-content: flex-start;
		min-height: 40px;
		padding-inline: 12px;
	}
	.list {
		flex: 1;
		min-height: 0;
		overflow-x: hidden;
		overflow-y: auto;
		padding: 0 0 12px;
	}
	.group + .group {
		margin-top: 18px;
	}
	.group-name {
		margin: 0 0 4px;
		padding: 0 10px;
		font: 600 12px/1.6 var(--sans);
		letter-spacing: 0.01em;
		color: var(--muted);
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: 1px;
	}
	.row {
		position: relative;
		display: flex;
		align-items: center;
		border-radius: var(--r-control);
		transition: background-color var(--dur-fast) ease;
	}
	.row a {
		flex: 1;
		min-width: 0;
		display: block;
		padding: 7px 10px;
		border-radius: var(--r-control);
		color: var(--ink);
		font-size: 14px;
		line-height: 1.45;
		text-decoration: none;
	}
	.row a.untitled {
		color: var(--muted);
	}
	.name {
		display: block;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}
	.row.current {
		background: var(--paper);
		box-shadow: 0 1px 2px rgb(20 22 24 / 0.08);
	}
	.row.current a {
		font-weight: 500;
	}
	@media (hover: hover) {
		.row:hover:not(.current) {
			background: rgb(20 22 24 / 0.05);
		}
	}
	/* The menu button shows on the current row, on hover and on keyboard focus; touch screens always show it. */
	.more {
		flex: none;
		display: grid;
		place-items: center;
		width: 30px;
		height: 30px;
		margin-right: 3px;
		padding: 0;
		border: 0;
		border-radius: 5px;
		background: transparent;
		color: var(--ink-2);
		cursor: pointer;
		opacity: 0;
		transition:
			opacity var(--dur-fast) ease,
			background-color var(--dur-fast) ease;
	}
	.row.current .more,
	.row.menu-open .more,
	.row:hover .more,
	.more:focus-visible {
		opacity: 1;
	}
	.more:hover,
	.row.menu-open .more {
		background: rgb(20 22 24 / 0.07);
	}
	@media (hover: none) {
		.more {
			opacity: 1;
		}
	}
	.menu {
		position: fixed;
		z-index: 80;
		display: grid;
		width: 172px;
		padding: 5px;
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: var(--r-panel);
		box-shadow: var(--shadow-pop);
	}
	.menu button {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 8px 10px;
		border: 0;
		border-radius: 5px;
		background: transparent;
		color: var(--ink);
		font-size: 14px;
		text-align: left;
		cursor: pointer;
	}
	.menu button:hover,
	.menu button:focus-visible {
		background: var(--desk);
		outline: none;
	}
	.menu .danger {
		color: var(--reject);
	}
	.rename {
		flex: 1;
		display: block;
		padding: 2px 0;
	}
	.rename .input {
		min-height: 34px;
		padding: 5px 9px;
		font-size: 14px;
	}
	.empty {
		padding: 4px 10px;
		color: var(--muted);
		line-height: 1.5;
	}
	.ghost {
		display: grid;
		gap: 14px;
		padding: 4px 10px;
	}
</style>
