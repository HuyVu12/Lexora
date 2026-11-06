<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { api, ApiError } from '#lib/api.js';
	import { session } from '#lib/session.svelte.js';
	import { t } from '#lib/i18n/index.svelte.js';
	import type { Account } from '#lib/types.js';

	let username = $state('');
	let password = $state('');
	let busy = $state(false);
	let error = $state('');
	const expired = $derived(page.url.searchParams.get('expired') === '1');

	function safeNext(): string {
		const next = page.url.searchParams.get('next') ?? '/';
		return next.startsWith('/') && !next.startsWith('//') && !next.startsWith('/login') ? next : '/';
	}

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		error = '';
		try {
			session.account = await api<Account>('/api/auth/login', { username, password });
			await goto(safeNext(), { replaceState: true });
		} catch (e) {
			error = e instanceof ApiError ? e.message : String(e);
			password = '';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>{t('login.title')} · Lexora</title></svelte:head>

<div class="wrap">
	<form class="sheet card" onsubmit={submit} aria-describedby={error ? 'login-error' : undefined}>
		<h1 class="title">{t('login.title')}</h1>
		<p class="lead">{t('login.lead')}</p>
		<p class="specimen serif" aria-hidden="true">
			<mark class="hl-condition">Khi kết thúc thời gian thử việc</mark>,
			<mark class="hl-actor">người sử dụng lao động</mark> <b>phải</b>
			<mark class="hl-action">thông báo</mark> <mark class="hl-object">kết quả thử việc</mark> cho
			<mark class="hl-party">người lao động</mark>.
		</p>
		{#if expired && !error}<p class="notice info" role="status">{t('login.expired')}</p>{/if}
		{#if error}<p id="login-error" class="notice error" role="alert">{error}</p>{/if}
		<label class="field">
			<span>{t('login.username')}</span>
			<input name="username" autocomplete="username" required bind:value={username} />
		</label>
		<label class="field">
			<span>{t('login.password')}</span>
			<input name="password" type="password" autocomplete="current-password" required bind:value={password} />
		</label>
		<button class="btn primary" type="submit" disabled={busy}>{busy ? t('login.busy') : t('login.submit')}</button>
		<p class="small muted">{t('login.hint')}</p>
		<p class="small muted legal">{t('app.legal')}</p>
	</form>
</div>

<style>
	.wrap {
		min-height: calc(100vh - var(--topbar));
		display: grid;
		place-items: center;
		padding: 32px 16px;
	}
	.card {
		width: min(440px, 100%);
		padding: 36px 36px 28px;
		display: grid;
		gap: 16px;
	}
	.specimen {
		font-size: 16px;
		line-height: 1.9;
		padding: 14px 16px;
		background: var(--desk);
		border-radius: var(--r-sheet);
	}
	.specimen mark {
		background: var(--hl);
		color: var(--ink);
		padding: 1px 2px;
		border-radius: 2px;
		box-decoration-break: clone;
		-webkit-box-decoration-break: clone;
	}
	.specimen b {
		font-weight: 600;
		border-bottom: 1.5px solid var(--ink);
	}
	.btn.primary {
		min-height: 44px;
	}
	.legal {
		border-top: 1px solid var(--rule);
		padding-top: 12px;
	}
</style>
