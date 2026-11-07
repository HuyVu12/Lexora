<script lang="ts">
	import '../app.css';
	import { onMount, type Snippet } from 'svelte';
	import { page } from '$app/state';
	import { goto, afterNavigate } from '$app/navigation';
	import { clearToast } from '#lib/toast.svelte.js';
	import TopBar from '#lib/components/TopBar.svelte';
	import Toast from '#lib/components/Toast.svelte';
	import GlossaryTip from '#lib/components/GlossaryTip.svelte';
	import { session } from '#lib/session.svelte.js';
	import { t } from '#lib/i18n/index.svelte.js';
	import type { Account } from '#lib/types.js';

	let { children }: { children: Snippet } = $props();
	const PUBLIC = ['/login', '/about'];
	// A message belongs to the screen that raised it.
	afterNavigate(({ from }) => {
		if (from) clearToast();
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
		if (session.checked && !session.account && !PUBLIC.includes(page.url.pathname)) {
			goto(`/login?next=${encodeURIComponent(page.url.pathname + page.url.search)}`, { replaceState: true });
		}
	});
</script>

<TopBar />
<main id="main" tabindex="-1">
	{#if !session.checked}
		<p class="page muted" aria-live="polite">{t('common.loading')}</p>
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
</style>
