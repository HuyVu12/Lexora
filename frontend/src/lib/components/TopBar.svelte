<script lang="ts">
	import { page } from '$app/state';
	import { goto, afterNavigate } from '$app/navigation';
	import Icon from './Icon.svelte';
	import { t, i18n } from '#lib/i18n/index.svelte.js';
	import { session, canReview, canMonitor } from '#lib/session.svelte.js';
	import { api } from '#lib/api.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	// Three everyday links stay on the bar; the four research pages share one menu; account management and
	// monitoring live in the avatar menu, so even an admin sees a short bar.
	type Item = { href: string; key: MessageKey; match: (p: string) => boolean };
	const account = $derived(session.account);
	const home: Item = { href: '/', key: 'nav.home', match: (p) => p === '/' || p.startsWith('/kb') };
	const chat: Item = { href: '/chat', key: 'nav.chat', match: (p) => p.startsWith('/chat') };
	const importing: Item = { href: '/import', key: 'nav.import', match: (p) => p.startsWith('/import') || p.startsWith('/drafts') };
	const results: Item = { href: '/research/results', key: 'nav.results', match: (p) => p.startsWith('/research/results') };
	const monitor: Item = { href: '/dev', key: 'nav.monitor', match: (p) => p.startsWith('/dev') };
	const users: Item = { href: '/admin/users', key: 'nav.users', match: (p) => p.startsWith('/admin') };
	const docs: Item = { href: '/docs', key: 'nav.docs', match: (p) => p.startsWith('/docs') };
	const research: Item[] = [
		{ href: '/research', key: 'nav.corpora', match: (p) => p.startsWith('/research') && !/^\/research\/(questions|gold|results)/.test(p) },
		{ href: '/research/questions', key: 'nav.questions', match: (p) => p.startsWith('/research/questions') },
		{ href: '/research/gold', key: 'nav.gold', match: (p) => p.startsWith('/research/gold') },
		results
	];
	// A dev account's work is monitoring, so its two pages stay on the bar.
	const links = $derived(canReview(account) ? [home, chat, importing] : account?.role === 'dev' ? [home, chat, monitor, results] : [home, chat]);
	const after = $derived(account ? [docs] : []);
	const manage = $derived([...(account?.role === 'admin' ? [users] : []), ...(account?.role === 'admin' && canMonitor(account) ? [monitor] : [])]);
	const inResearch = $derived(research.some((item) => item.match(page.url.pathname)));

	let open = $state<'' | 'research' | 'user'>('');
	afterNavigate(() => (open = ''));
	const toggle = (menu: 'research' | 'user') => (open = open === menu ? '' : menu);

	function outside(event: MouseEvent) {
		if (open && !(event.target as Element).closest('.has-menu')) open = '';
	}
	function escape(event: KeyboardEvent) {
		if (event.key === 'Escape' && open) {
			const which = open;
			open = '';
			document.getElementById(`${which}-button`)?.focus();
		}
	}

	async function logout() {
		await api('/api/auth/logout', {}).catch(() => undefined);
		session.account = null;
		open = '';
		await goto('/login');
	}
</script>

<svelte:window onclick={outside} onkeydown={escape} />

<header class="topbar">
	<a class="skip" href="#main">{t('nav.skip')}</a>
	<a class="brand" href="/" aria-label="Lexora">
		<svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true"
			><rect width="32" height="32" rx="6" fill="#2a2d30" /><rect x="7" y="20" width="18" height="5" rx="1" fill="#ffe36e" /><path
				d="M11 7v15h11"
				fill="none"
				stroke="#fff"
				stroke-width="3"
				stroke-linecap="square"
			/></svg
		>
		<span>Lexora</span>
	</a>
	{#if account}
		<nav aria-label={t('nav.main')}>
			{#each links as item (item.href)}
				<a href={item.href} aria-current={item.match(page.url.pathname) ? 'page' : undefined}>{t(item.key)}</a>
			{/each}
			{#if canReview(account)}
				<div class="has-menu research">
					<button type="button" id="research-button" class="nav-button" class:current={inResearch} aria-expanded={open === 'research'}
						aria-controls="research-menu" onclick={() => toggle('research')}>{t('nav.zone.research')}<Icon name="chevron" size={16} /></button>
					{#if open === 'research'}
						<div class="drop" id="research-menu">
							{#each research as item (item.href)}
								<a href={item.href} aria-current={item.match(page.url.pathname) ? 'page' : undefined}>{t(item.key)}</a>
							{/each}
						</div>
					{/if}
				</div>
			{/if}
			{#each after as item (item.href)}
				<a href={item.href} aria-current={item.match(page.url.pathname) ? 'page' : undefined}>{t(item.key)}</a>
			{/each}
		</nav>
	{/if}
	<div class="end">
		<a class="about" href="/about" aria-current={page.url.pathname === '/about' ? 'page' : undefined}>{t('nav.about')}</a>
		<button type="button" class="lang" aria-label={t('lang.label')} onclick={() => i18n.set(i18n.locale === 'vi' ? 'en' : 'vi')}>
			<Icon name="globe" size={16} /><span class="lang-text">{t('lang.switchTo')}</span>
		</button>
		{#if account}
			<div class="user has-menu">
				<button type="button" id="user-button" class="who" class:current={manage.some((item) => item.match(page.url.pathname))}
					aria-expanded={open === 'user'} aria-controls="user-menu" onclick={() => toggle('user')}>
					<span class="avatar" aria-hidden="true">{account.display_name.slice(0, 1).toUpperCase()}</span>
					<span class="name" title={account.display_name}><span class="full">{account.display_name}</span><small>{t(`role.${account.role}`)}</small></span>
					<Icon name="chevron" size={16} />
				</button>
				{#if open === 'user'}
					<div class="menu" id="user-menu">
						<div class="who-card">
							<strong>{account.display_name}</strong>
							<span class="small muted">@{account.username} · {t(`role.${account.role}`)}</span>
						</div>
						<div class="menu-links" class:phone-only={!manage.length}>
							{#each manage as item (item.href)}
								<a href={item.href} aria-current={item.match(page.url.pathname) ? 'page' : undefined}>{t(item.key)}</a>
							{/each}
							<!-- On phones the bar hides Documents, so the avatar menu carries it. -->
							<a class="phone-only" href={docs.href} aria-current={docs.match(page.url.pathname) ? 'page' : undefined}>{t(docs.key)}</a>
						</div>
						<button type="button" class="btn quiet small" onclick={logout}><Icon name="logout" size={16} />{t('user.logout')}</button>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</header>

<style>
	.topbar {
		position: sticky;
		top: 0;
		z-index: 40;
		height: var(--topbar);
		display: flex;
		align-items: center;
		gap: 28px;
		padding: 0 20px;
		background: var(--paper);
		border-bottom: 1px solid var(--rule);
	}
	.skip {
		position: absolute;
		left: 8px;
		top: -48px;
		padding: 8px 12px;
		background: var(--graphite);
		color: #fff;
		border-radius: 6px;
	}
	.skip:focus {
		top: 8px;
	}
	.brand {
		display: flex;
		align-items: center;
		gap: 10px;
		color: var(--ink);
		text-decoration: none;
		font: 600 19px/1 var(--serif);
	}
	nav {
		display: flex;
		align-items: center;
		gap: 2px;
		height: 100%;
	}
	nav > a,
	.nav-button,
	.about {
		position: relative;
		display: inline-flex;
		align-items: center;
		gap: 4px;
		height: 36px;
		padding: 0 12px;
		border: 0;
		border-radius: var(--r-control);
		background: none;
		color: var(--ink-2);
		font: inherit;
		font-weight: 500;
		text-decoration: none;
		white-space: nowrap;
		cursor: pointer;
	}
	nav > a:hover,
	.nav-button:hover,
	.about:hover {
		background: var(--desk);
		color: var(--ink);
	}
	nav > a[aria-current='page'],
	.nav-button.current,
	.about[aria-current='page'] {
		color: var(--ink);
		background: var(--desk);
	}
	nav > a[aria-current='page']::after,
	.nav-button.current::after {
		content: '';
		position: absolute;
		left: 12px;
		right: 12px;
		bottom: -10px;
		height: 2px;
		border-radius: 2px;
		background: var(--graphite);
	}
	.has-menu {
		position: relative;
	}
	.research {
		margin-left: 10px;
		padding-left: 12px;
		border-left: 1px solid var(--rule);
	}
	.nav-button :global(svg),
	.who :global(svg:last-child) {
		color: var(--muted);
		transition: transform 0.15s var(--ease-out);
	}
	[aria-expanded='true'] :global(svg:last-child) {
		transform: rotate(180deg);
	}
	.drop,
	.menu {
		position: absolute;
		top: calc(100% + 8px);
		min-width: 200px;
		padding: 6px;
		display: grid;
		gap: 2px;
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: var(--r-panel);
		box-shadow: var(--shadow-pop);
	}
	.drop {
		left: 12px;
	}
	.menu {
		right: 0;
		min-width: 230px;
	}
	.drop a,
	.menu-links a {
		display: flex;
		align-items: center;
		min-height: 36px;
		padding: 0 10px;
		border-radius: var(--r-control);
		color: var(--ink-2);
		font-weight: 500;
		text-decoration: none;
	}
	.drop a:hover,
	.menu-links a:hover {
		background: var(--desk);
		color: var(--ink);
	}
	.drop a[aria-current='page'],
	.menu-links a[aria-current='page'] {
		background: var(--desk);
		color: var(--ink);
		font-weight: 600;
	}
	.who-card {
		display: grid;
		gap: 1px;
		padding: 6px 10px 8px;
		border-bottom: 1px solid var(--rule);
		margin-bottom: 4px;
	}
	.menu-links {
		display: grid;
		gap: 2px;
		padding-bottom: 4px;
		margin-bottom: 4px;
		border-bottom: 1px solid var(--rule);
	}
	.menu .btn {
		justify-content: flex-start;
	}
	.end {
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: 8px;
		flex-shrink: 0;
	}
	.lang {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		height: 36px;
		padding: 0 10px;
		border: 1px solid var(--rule);
		border-radius: var(--r-control);
		background: var(--paper);
		color: var(--ink-2);
		cursor: pointer;
	}
	.lang:hover {
		border-color: var(--ink-2);
	}
	.who {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 4px 6px 4px 4px;
		border: 0;
		border-radius: var(--r-control);
		background: transparent;
		cursor: pointer;
		text-align: left;
	}
	.who:hover,
	.who.current {
		background: var(--desk);
	}
	.avatar {
		width: 30px;
		height: 30px;
		border-radius: 50%;
		display: grid;
		place-items: center;
		flex-shrink: 0;
		background: var(--graphite);
		color: #fff;
		font-weight: 600;
	}
	.name {
		display: grid;
		max-width: 150px;
		line-height: 1.2;
		font-weight: 500;
	}
	.full {
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}
	.name small {
		font-size: 12px;
		color: var(--muted);
		font-weight: 400;
	}
	.brand span {
		white-space: nowrap;
	}
	button:focus-visible,
	nav a:focus-visible,
	.drop a:focus-visible,
	.menu-links a:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	@media (max-width: 1180px) {
		.name {
			display: none;
		}
	}
	@media (max-width: 960px) {
		.topbar {
			gap: 14px;
		}
		.lang-text,
		.about {
			display: none;
		}
	}
	@media (max-width: 860px) {
		.topbar {
			gap: 10px;
			padding: 0 12px;
		}
		.brand span {
			display: none;
		}
		nav > a,
		.nav-button {
			padding: 0 9px;
		}
	}
	.menu .phone-only {
		display: none;
	}
	@media (max-width: 760px) {
		.menu .menu-links.phone-only {
			display: grid;
		}
		.menu .menu-links a.phone-only {
			display: flex;
		}
		/* Phones are for looking things up; authoring and research open from the overview's buttons, admin from the avatar menu. */
		nav > a[href='/import'],
		nav > a[href='/research/results'],
		nav > a[href='/docs'],
		.research {
			display: none;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.nav-button :global(svg),
		.who :global(svg:last-child) {
			transition: none;
		}
	}
</style>
