<script lang="ts">
	import '../app.css';
	import { onMount, type Snippet } from 'svelte';
	import { page, navigating } from '$app/state';
	import { goto, afterNavigate, onNavigate } from '$app/navigation';
	import { clearToast } from '#lib/toast.svelte.js';
	import TopBar from '#lib/components/TopBar.svelte';
	import Toast from '#lib/components/Toast.svelte';
	import GlossaryTip from '#lib/components/GlossaryTip.svelte';
	import Skeleton from '#lib/components/Skeleton.svelte';
	import { session } from '#lib/session.svelte.js';
	import { activity } from '#lib/activity.svelte.js';
	import { clearAppState } from '#lib/app-state.svelte.js';
	import { reducedMotion } from '#lib/motion.js';
	import { t } from '#lib/i18n/index.svelte.js';
	import type { Account } from '#lib/types.js';

	let { children }: { children: Snippet } = $props();
	const PUBLIC = ['/login', '/about'];
	// A message belongs to the screen that raised it.
	afterNavigate(({ from }) => {
		if (from) clearToast();
	});

	// Page changes cross-fade through the View Transitions API: the old page fades out fast, the new one
	// settles in from a few pixels below (CSS in app.css). Browsers without it, reduced motion, and moves
	// within one page (a query string, a chat switching session) change instantly.
	onNavigate((navigation) => {
		if (!document.startViewTransition || reducedMotion()) return;
		if (navigation.from?.route.id === navigation.to?.route.id) return;
		return new Promise<void>((resolve) => {
			const transition = document.startViewTransition(async () => {
				resolve();
				await navigation.complete;
			});
			// A navigation that is cancelled or overtaken skips its transition; that is not an error.
			transition.ready.catch(() => undefined);
			transition.finished.catch(() => undefined);
			transition.updateCallbackDone.catch(() => undefined);
		});
	});

	onMount(async () => {
		try {
			const response = await fetch('/api/auth/me', { credentials: 'same-origin' });
			session.account = response.ok ? ((await response.json()) as Account) : null;
		} finally {
			session.checked = true;
		}
	});

	$effect(() => {
		if (session.checked && !session.account) clearAppState();
		if (session.checked && !session.account && !PUBLIC.includes(page.url.pathname)) {
			goto(`/login?next=${encodeURIComponent(page.url.pathname + page.url.search)}`, { replaceState: true });
		}
	});

	// The thin bar under the top bar: shown only when a page change or a request runs long enough to notice.
	const busy = $derived(!!navigating.to || activity.requests > 0);
</script>

<TopBar />
<div class="progress" class:busy aria-hidden="true"><i></i></div>
<main id="main" tabindex="-1">
	{#if !session.checked}
		<div class="page boot" aria-busy="true">
			<span class="visually-hidden" role="status">{t('common.loading')}</span>
			<Skeleton width="280px" height="30px" />
			<Skeleton lines={2} width="560px" last="380px" />
		</div>
	{:else if session.account || PUBLIC.includes(page.url.pathname)}
		{@render children()}
	{/if}
</main>
<Toast />
<GlossaryTip />

<style>
	main:focus {
		outline: none;
	}
	.boot {
		display: grid;
		gap: 14px;
		max-width: 1320px;
	}
	.boot :global(.lines) {
		max-width: 100%;
	}
	.progress {
		position: fixed;
		top: calc(var(--topbar) - 1px);
		left: 0;
		right: 0;
		z-index: 41;
		height: 2px;
		overflow: hidden;
		opacity: 0;
		pointer-events: none;
		transition: opacity var(--dur-base) ease;
	}
	/* Only a wait longer than ~400 ms shows the bar; quick answers never blink it. */
	.progress.busy {
		opacity: 1;
		transition-delay: 400ms;
	}
	.progress i {
		position: absolute;
		inset: 0;
		width: 40%;
		background: linear-gradient(90deg, transparent, var(--graphite) 30%, var(--graphite) 70%, transparent);
		transform: translateX(-100%);
	}
	.progress.busy i {
		animation: travel 1.1s var(--ease-in-out) infinite;
	}
	@keyframes travel {
		to {
			transform: translateX(250%);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.progress.busy i {
			animation: none;
			width: 100%;
			transform: none;
			opacity: 0.5;
		}
	}
</style>
