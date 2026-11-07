<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import Icon from './Icon.svelte';
	import { t, i18n } from '#lib/i18n/index.svelte.js';
	import { session, canReview } from '#lib/session.svelte.js';
	import { api } from '#lib/api.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	type Item = { href: string; key: MessageKey; match: (p: string) => boolean };
	const account = $derived(session.account);
	const lookup: Item[] = [
		{ href: '/', key: 'nav.home', match: (p) => p === '/' || p.startsWith('/kb') },
		{ href: '/chat', key: 'nav.chat', match: (p) => p.startsWith('/chat') }
	];
	const author: Item[] = [{ href: '/import', key: 'nav.import', match: (p) => p.startsWith('/import') || p.startsWith('/drafts') }];
	const research: Item[] = [
		{ href: '/research', key: 'nav.corpora', match: (p) => p.startsWith('/research') && !p.startsWith('/research/questions') },
		{ href: '/research/questions', key: 'nav.questions', match: (p) => p.startsWith('/research/questions') }
	];
	const admin: Item[] = [{ href: '/admin/users', key: 'nav.users', match: (p) => p.startsWith('/admin') }];
	const groups = $derived([
		{ key: 'nav.zone.lookup' as MessageKey, items: lookup },
		...(canReview(account) ? [{ key: 'nav.zone.author' as MessageKey, items: author }] : []),
		...(canReview(account) ? [{ key: 'nav.zone.research' as MessageKey, items: research }] : []),
		...(account?.role === 'admin' ? [{ key: 'nav.zone.admin' as MessageKey, items: admin }] : [])
	]);

	let menuOpen = $state(false);

	async function logout() {
		await api('/api/auth/logout', {}).catch(() => undefined);
		session.account = null;
		menuOpen = false;
		await goto('/login');
	}
</script>

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
			{#each groups as group (group.key)}
				<div class="group" role="group" aria-label={t(group.key)}>
					{#each group.items as item (item.href)}
						<a href={item.href} aria-current={item.match(page.url.pathname) ? 'page' : undefined}>{t(item.key)}</a>
					{/each}
				</div>
			{/each}
		</nav>
	{/if}
	<div class="end">
		<a class="about" href="/about" aria-current={page.url.pathname === '/about' ? 'page' : undefined}>{t('nav.about')}</a>
		<button type="button" class="lang" aria-label={t('lang.label')} onclick={() => i18n.set(i18n.locale === 'vi' ? 'en' : 'vi')}>
			<Icon name="globe" size={16} /><span class="lang-text">{t('lang.switchTo')}</span>
		</button>
		{#if account}
			<div class="user">
				<button type="button" class="who" aria-expanded={menuOpen} aria-haspopup="true" onclick={() => (menuOpen = !menuOpen)}>
					<span class="avatar" aria-hidden="true">{account.display_name.slice(0, 1).toUpperCase()}</span>
					<span class="name">{account.display_name}<small>{t(`role.${account.role}`)}</small></span>
				</button>
				{#if menuOpen}
					<div class="menu">
						<p class="small muted">@{account.username}</p>
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
		gap: 20px;
		height: 100%;
	}
	.group {
		display: flex;
		gap: 2px;
		align-items: center;
	}
	.group + .group {
		padding-left: 20px;
		border-left: 1px solid var(--rule);
	}
	nav a,
	.about {
		position: relative;
		display: inline-flex;
		align-items: center;
		height: 36px;
		padding: 0 12px;
		border-radius: var(--r-control);
		color: var(--ink-2);
		font-weight: 500;
		text-decoration: none;
	}
	nav a:hover,
	.about:hover {
		background: var(--desk);
		color: var(--ink);
	}
	nav a[aria-current='page'],
	.about[aria-current='page'] {
		color: var(--ink);
		background: var(--desk);
	}
	nav a[aria-current='page']::after {
		content: '';
		position: absolute;
		left: 12px;
		right: 12px;
		bottom: -10px;
		height: 2px;
		border-radius: 2px;
		background: var(--graphite);
	}
	.end {
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: 8px;
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
	.user {
		position: relative;
	}
	.who {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 4px 8px 4px 4px;
		border: 0;
		border-radius: var(--r-control);
		background: transparent;
		cursor: pointer;
		text-align: left;
	}
	.who:hover {
		background: var(--desk);
	}
	.avatar {
		width: 30px;
		height: 30px;
		border-radius: 50%;
		display: grid;
		place-items: center;
		background: var(--graphite);
		color: #fff;
		font-weight: 600;
	}
	.name {
		display: grid;
		line-height: 1.2;
		font-weight: 500;
	}
	.name small {
		font-size: 12px;
		color: var(--muted);
		font-weight: 400;
	}
	.menu {
		position: absolute;
		right: 0;
		top: calc(100% + 6px);
		min-width: 200px;
		padding: 10px;
		display: grid;
		gap: 6px;
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: var(--r-panel);
		box-shadow: var(--shadow-pop);
	}
	.menu .btn {
		justify-content: flex-start;
	}
	nav a,
	.brand span {
		white-space: nowrap;
	}
	@media (max-width: 900px) {
		.topbar {
			gap: 12px;
			padding: 0 12px;
		}
		.brand span,
		.lang-text {
			display: none;
		}
		nav a {
			padding: 0 9px;
		}
		.name,
		.about {
			display: none;
		}
		.group + .group {
			padding-left: 8px;
		}
	}
	@media (max-width: 760px) {
		/* Phones are for looking things up; authoring and admin open from the overview's buttons. */
		.group + .group {
			display: none;
		}
	}
</style>
