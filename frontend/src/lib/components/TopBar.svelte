<script lang="ts">
	import { page } from '$app/state';
	import { goto, afterNavigate } from '$app/navigation';
	import Icon from './Icon.svelte';
	import { t, i18n, preloadLocale } from '#lib/i18n/index.svelte.js';
	import { session, canReview, canMonitor } from '#lib/session.svelte.js';
	import { api } from '#lib/api.js';
	import { clearAppState } from '#lib/app-state.svelte.js';
	import { pop, popOut } from '#lib/motion.js';
	import TourPicker from './TourPicker.svelte';
	import { tourStatus, startTour, toursFor } from '#lib/tour/tour.svelte.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	// Three everyday links stay on the bar; the four research pages share one menu; account management and
	// monitoring live in the avatar menu, so even an admin sees a short bar.
	// `tour` is the item's data-tour id, the anchor the step-by-step tours point at.
	type Item = { href: string; key: MessageKey; match: (p: string) => boolean; tour?: string };
	const account = $derived(session.account);
	const home: Item = { href: '/', key: 'nav.home', tour: 'nav-home', match: (p) => p === '/' || p.startsWith('/kb') };
	const chat: Item = { href: '/chat', key: 'nav.chat', tour: 'nav-chat', match: (p) => p.startsWith('/chat') };
	const importing: Item = { href: '/import', key: 'nav.import', tour: 'nav-import', match: (p) => p.startsWith('/import') || p.startsWith('/drafts') };
	const results: Item = { href: '/research/results', key: 'nav.results', match: (p) => p.startsWith('/research/results') };
	const monitor: Item = { href: '/dev', key: 'nav.monitor', tour: 'nav-monitor', match: (p) => p.startsWith('/dev') };
	const users: Item = { href: '/admin/users', key: 'nav.users', match: (p) => p.startsWith('/admin') };
	const docs: Item = { href: '/docs', key: 'nav.docs', tour: 'nav-docs', match: (p) => p.startsWith('/docs') };
	const research: Item[] = [
		{ href: '/research', key: 'nav.corpora', match: (p) => p.startsWith('/research') && !/^\/research\/(questions|gold|audit|results)/.test(p) },
		{ href: '/research/questions', key: 'nav.questions', match: (p) => p.startsWith('/research/questions') },
		{ href: '/research/gold', key: 'nav.gold', match: (p) => p.startsWith('/research/gold') },
		{ href: '/research/audit', key: 'nav.audit', match: (p) => p.startsWith('/research/audit') },
		results
	];
	// A dev account's work is monitoring, so its two pages stay on the bar.
	const links = $derived(canReview(account) ? [home, chat, importing] : account?.role === 'dev' ? [home, chat, monitor, results] : [home, chat]);
	const after = $derived(account ? [docs] : []);
	const manage = $derived([...(account?.role === 'admin' ? [users] : []), ...(account?.role === 'admin' && canMonitor(account) ? [monitor] : [])]);
	// On phones the bar keeps only Overview and Ask; a dev account's two work pages move into the avatar menu.
	const phoneMenu = $derived(account?.role === 'dev' ? [monitor, results] : []);
	const inResearch = $derived(research.some((item) => item.match(page.url.pathname)));
	// The avatar menu shows one "step-by-step guides" item; it swaps the menu's content for the tour picker.
	const tours = $derived(toursFor(account?.role ?? null));
	const toursSeen = $derived(tours.filter((x) => tourStatus(x.id) === 'done').length);
	let userView = $state<'main' | 'tours'>('main');
	function beginTour(id: string) {
		open = '';
		startTour(id);
	}
	function closePicker() {
		userView = 'main';
		requestAnimationFrame(() => document.querySelector<HTMLElement>('#user-menu .tour-open')?.focus());
	}

	let open = $state<'' | 'research' | 'user'>('');
	afterNavigate(() => (open = ''));
	const toggle = (menu: 'research' | 'user') => {
		userView = 'main';
		open = open === menu ? '' : menu;
	};

	function outside(event: MouseEvent) {
		// The path as dispatched: a click that swaps the menu's view removes its own button before this runs.
		if (open && !event.composedPath().some((node) => node instanceof Element && node.classList.contains('has-menu'))) open = '';
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
		clearAppState();
		open = '';
		await goto('/login');
	}

	// One underline slides between the bar's items instead of each item drawing its own: it shows where you
	// are and, as it travels, where you came from. Measured from the current item; transform-only.
	let navEl = $state<HTMLElement | null>(null);
	let mark = $state({ x: 0, w: 0, shown: false, ready: false });
	function measure() {
		const current = navEl?.querySelector<HTMLElement>(':scope > a[aria-current="page"], .nav-button.current');
		if (!navEl || !current) {
			mark.shown = false;
			return;
		}
		const nav = navEl.getBoundingClientRect();
		const box = current.getBoundingClientRect();
		mark.x = box.left - nav.left + 12;
		mark.w = Math.max(0, box.width - 24);
		mark.shown = true;
	}
	$effect(() => {
		// Re-measure when the place, the items or their language change.
		void page.url.pathname;
		void links.length;
		void i18n.locale;
		if (!navEl) return;
		const frame = requestAnimationFrame(() => {
			measure();
			// The first placement is instant; only later moves slide.
			if (!mark.ready) requestAnimationFrame(() => (mark.ready = true));
		});
		return () => cancelAnimationFrame(frame);
	});
	$effect(() => {
		if (!navEl) return;
		const observer = new ResizeObserver(() => measure());
		observer.observe(navEl);
		document.fonts?.ready.then(() => measure());
		return () => observer.disconnect();
	});
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
		<nav aria-label={t('nav.main')} bind:this={navEl}>
			{#each links as item (item.href)}
				<a href={item.href} data-tour={item.tour} aria-current={item.match(page.url.pathname) ? 'page' : undefined}>{t(item.key)}</a>
			{/each}
			{#if canReview(account)}
				<div class="has-menu research">
					<button type="button" id="research-button" data-tour="nav-research" class="nav-button" class:current={inResearch} aria-expanded={open === 'research'}
						aria-controls="research-menu" onclick={() => toggle('research')}>{t('nav.zone.research')}<Icon name="chevron" size={16} /></button>
					{#if open === 'research'}
						<div class="drop" id="research-menu" in:pop={{ origin: 'top left' }} out:popOut>
							{#each research as item (item.href)}
								<a href={item.href} aria-current={item.match(page.url.pathname) ? 'page' : undefined}>{t(item.key)}</a>
							{/each}
						</div>
					{/if}
				</div>
			{/if}
			{#each after as item (item.href)}
				<a href={item.href} data-tour={item.tour} aria-current={item.match(page.url.pathname) ? 'page' : undefined}>{t(item.key)}</a>
			{/each}
			<span class="mark" class:shown={mark.shown} class:ready={mark.ready} style:transform="translateX({mark.x}px) scaleX({mark.w})" aria-hidden="true"></span>
		</nav>
	{/if}
	<div class="end">
		<a class="about" href="/about" aria-current={page.url.pathname === '/about' ? 'page' : undefined}>{t('nav.about')}</a>
		<button type="button" class="lang" data-tour="lang-switch" aria-label={t('lang.label')} onpointerenter={() => preloadLocale('en')} onfocus={() => preloadLocale('en')}
			onclick={() => i18n.set(i18n.locale === 'vi' ? 'en' : 'vi')}>
			<Icon name="globe" size={16} /><span class="lang-text">{t('lang.switchTo')}</span>
		</button>
		{#if account}
			<div class="user has-menu">
				<button type="button" id="user-button" data-tour="user-menu" class="who" class:current={manage.some((item) => item.match(page.url.pathname))}
					aria-expanded={open === 'user'} aria-controls="user-menu" onclick={() => toggle('user')}>
					<span class="avatar" aria-hidden="true">{account.display_name.slice(0, 1).toUpperCase()}</span>
					<span class="name" title={account.display_name}><span class="full">{account.display_name}</span><small>{t(`role.${account.role}`)}</small></span>
					<Icon name="chevron" size={16} />
				</button>
				{#if open === 'user'}
					<div class="menu" class:picking={userView === 'tours'} id="user-menu" data-tour-part="user-menu" in:pop={{ origin: 'top right' }} out:popOut>
						{#if userView === 'tours'}
							<TourPicker {tours} role={account.role} path={page.url.pathname} onpick={beginTour} onback={closePicker} />
						{:else}
						<div class="who-card">
							<strong>{account.display_name}</strong>
							<span class="small muted">@{account.username} · {t(`role.${account.role}`)}</span>
						</div>
						<div class="menu-links" class:phone-only={!manage.length}>
							{#each manage as item (item.href)}
								<a href={item.href} aria-current={item.match(page.url.pathname) ? 'page' : undefined}>{t(item.key)}</a>
							{/each}
							<!-- On phones the bar hides these, so the avatar menu carries them. -->
							{#each phoneMenu as item (item.href)}
								<a class="phone-only" href={item.href} aria-current={item.match(page.url.pathname) ? 'page' : undefined}>{t(item.key)}</a>
							{/each}
							<a class="phone-only" href={docs.href} aria-current={docs.match(page.url.pathname) ? 'page' : undefined}>{t(docs.key)}</a>
						</div>
						{#if tours.length}
							<div class="menu-tours">
								<button type="button" class="tour-open" onclick={() => (userView = 'tours')}>
									<Icon name="route" size={16} />
									<span>{t('tour.menu.title')}</span>
									<span class="seen">{t('tour.menu.seen', { done: toursSeen, n: tours.length })}</span>
									<Icon name="chevron" size={16} />
								</button>
							</div>
						{/if}
						<button type="button" class="btn quiet small" onclick={logout}><Icon name="logout" size={16} />{t('user.logout')}</button>
						{/if}
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
		position: relative;
		display: flex;
		align-items: center;
		gap: 2px;
		height: 100%;
	}
	.mark {
		position: absolute;
		left: 0;
		bottom: -1px;
		width: 1px;
		height: 2px;
		background: var(--graphite);
		transform-origin: 0 50%;
		opacity: 0;
		pointer-events: none;
	}
	.mark.shown {
		opacity: 1;
	}
	.mark.ready {
		transition:
			transform var(--dur-slow) var(--ease-out),
			opacity var(--dur-fast) ease;
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
		transition:
			background-color var(--dur-fast) ease,
			color var(--dur-fast) ease;
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
	}
	.about[aria-current='page'] {
		background: var(--desk);
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
		transition: transform var(--dur-base) var(--ease-out);
	}
	[aria-expanded='true'] :global(svg:last-child) {
		transform: rotate(180deg);
	}
	.drop,
	.menu {
		position: absolute;
		z-index: 1;
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
		transition: background-color var(--dur-fast) ease;
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
	.menu-tours {
		display: grid;
		gap: 2px;
		padding-bottom: 4px;
		margin-bottom: 4px;
		border-bottom: 1px solid var(--rule);
	}
	.tour-open {
		display: flex;
		align-items: center;
		gap: 10px;
		min-height: 36px;
		padding: 0 6px 0 10px;
		border: 0;
		border-radius: var(--r-control);
		background: none;
		color: var(--ink-2);
		font: inherit;
		font-weight: 500;
		text-align: left;
		white-space: nowrap;
		cursor: pointer;
		transition: background-color var(--dur-fast) ease;
	}
	.tour-open > span:first-of-type {
		flex: 1;
	}
	.tour-open :global(svg) {
		flex: none;
		color: var(--flag);
	}
	.tour-open :global(svg:last-child) {
		color: var(--muted);
		transform: rotate(-90deg);
	}
	.tour-open .seen {
		font-size: 12.5px;
		font-weight: 400;
		color: var(--muted);
		font-variant-numeric: tabular-nums;
	}
	.tour-open:hover {
		background: var(--desk);
		color: var(--ink);
	}
	/* The picker needs a little more width than the menu so every tour name fits on one line. */
	.menu.picking {
		width: min(320px, calc(100vw - 24px));
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
	.lang:active,
	.who:active {
		transform: scale(0.97);
	}
	.lang,
	.who {
		transition:
			border-color var(--dur-fast) ease,
			background-color var(--dur-fast) ease,
			transform var(--dur-press) var(--ease-out);
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
		nav > a[href='/dev'],
		.research {
			display: none;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.nav-button :global(svg),
		.who :global(svg:last-child),
		.mark.ready {
			transition: none;
		}
	}
</style>
