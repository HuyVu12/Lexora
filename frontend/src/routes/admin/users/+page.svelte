<script lang="ts">
	import PageGuide from '#lib/components/PageGuide.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import Skeleton from '#lib/components/Skeleton.svelte';
	import { rise } from '#lib/motion.js';
	import { api } from '#lib/api.js';
	import { t, formatDay } from '#lib/i18n/index.svelte.js';
	import { session } from '#lib/session.svelte.js';
	import { notify, act } from '#lib/toast.svelte.js';
	import type { Account, Role } from '#lib/types.js';

	const ROLES: Role[] = ['reader', 'reviewer', 'dev', 'admin'];
	let accounts = $state<Account[] | null>(null);
	const active = $derived(accounts?.filter((a) => a.active).length ?? 0);
	let username = $state('');
	let displayName = $state('');
	let role = $state<Role>('reader');
	let password = $state('');
	let resetFor = $state<Account | null>(null);
	let newPassword = $state('');
	let busy = $state(false);

	const load = () => api<{ accounts: Account[] }>('/api/users').then((r) => (accounts = r.accounts)).catch((e) => notify(e.message, true));
	$effect(() => {
		if (session.account?.role === 'admin') load();
	});

	async function create(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		const ok = await act(async () => {
			const made = await api<Account>('/api/users', { username, display_name: displayName, role, password });
			notify({ key: 'users.created', params: { name: made.username } });
		});
		busy = false;
		if (ok) {
			username = displayName = password = '';
			role = 'reader';
			load();
		}
	}

	async function update(body: Record<string, unknown>) {
		if (await act(() => api('/api/users/update', body))) {
			notify({ key: 'users.updated' });
			load();
		}
	}

	async function reset(event: SubmitEvent) {
		event.preventDefault();
		if (!resetFor) return;
		await update({ id: resetFor.id, password: newPassword });
		resetFor = null;
		newPassword = '';
	}
</script>

<svelte:head><title>{t('users.title')} · Lexora</title></svelte:head>

<div class="page">
	{#if session.account?.role !== 'admin'}
		<h1 class="title">{t('common.forbidden.title')}</h1>
	{:else}
		<header class="page-head">
			<div>
				<h1 class="title">{t('users.title')}</h1>
				<p class="facts">
					{#if accounts}
						<span><strong>{accounts.length}</strong> {t('users.facts.n', { n: accounts.length })}</span>
						<span><strong>{active}</strong> {t('users.facts.active', { n: active })}</span>
						{#if accounts.length > active}<span><strong>{accounts.length - active}</strong> {t('users.facts.locked', { n: accounts.length - active })}</span>{/if}
					{:else}
						<span><Skeleton width="90px" height="12px" /></span><span><Skeleton width="120px" height="12px" /></span>
					{/if}
				</p>
			</div>
		</header>
		<PageGuide name="users" steps={3} />
		<div class="layout">
			<section class="panel list" data-tour="users-list" aria-busy={!accounts}>
				<table class="table">
					<thead>
						<tr><th scope="col">{t('users.username')}</th><th scope="col">{t('users.role')}</th><th scope="col">{t('users.status')}</th><th scope="col">{t('users.actions')}</th></tr>
					</thead>
					<tbody>
						{#if !accounts}
							{#each [0, 1, 2, 3, 4] as i (i)}
								<tr aria-hidden="true">
									<td><Skeleton width="130px" height="14px" /><span class="gap"></span><Skeleton width="160px" height="11px" /></td>
									<td><Skeleton width="136px" height="34px" radius="6px" /></td>
									<td><Skeleton width="110px" height="22px" radius="999px" /></td>
									<td><Skeleton width="200px" height="32px" radius="6px" /></td>
								</tr>
							{/each}
						{/if}
						{#each accounts ?? [] as a (a.id)}
							{@const me = a.id === session.account.id}
							<tr class:locked={!a.active}>
								<td>
									<strong>{a.display_name}</strong>{#if me}<span class="chip">{t('users.you')}</span>{/if}
									<br /><span class="small muted">@{a.username} · {formatDay(a.created_at)}</span>
								</td>
								<td>
									<label><span class="visually-hidden">{t('users.role')} {a.username}</span>
										<select class="input" value={a.role} disabled={me} onchange={(e) => update({ id: a.id, role: e.currentTarget.value })}>
											{#each ROLES as r (r)}<option value={r}>{t(`role.${r}`)}</option>{/each}
										</select>
									</label>
								</td>
								<td><span class="chip" class:public={a.active} class:synthetic={!a.active}>{a.active ? t('users.active') : t('users.locked')}</span></td>
								<td>
									<div class="row">
										<button type="button" class="btn small" disabled={me} onclick={() => update({ id: a.id, active: !a.active })}><Icon name="lock" />{a.active ? t('users.lock') : t('users.unlock')}</button>
										<button type="button" class="btn quiet small" aria-expanded={resetFor?.id === a.id} onclick={() => (resetFor = resetFor?.id === a.id ? null : a)}>{t('users.reset')}</button>
									</div>
								</td>
							</tr>
							{#if resetFor?.id === a.id}
								<tr class="reset-row">
									<td colspan="4">
										<form class="reset" onsubmit={reset} in:rise={{ y: -4 }}>
											<label class="field"><span>{t('users.newPassword', { name: a.username })}</span>
												<input type="password" autocomplete="new-password" minlength="10" required bind:value={newPassword} />
												<span class="hint">{t('users.passwordHint')}</span>
											</label>
											<div class="row"><button class="btn primary small" type="submit">{t('users.reset')}</button><button class="btn quiet small" type="button" onclick={() => (resetFor = null)}>{t('common.cancel')}</button></div>
										</form>
									</td>
								</tr>
							{/if}
						{/each}
					</tbody>
				</table>
			</section>
			<form class="panel create" data-tour="users-create" onsubmit={create}>
				<h2 class="heading">{t('users.create')}</h2>
				<label class="field"><span>{t('users.username')}</span><input autocomplete="off" required minlength="3" maxlength="64" pattern="[A-Za-z0-9._\-]+" bind:value={username} /></label>
				<label class="field"><span>{t('users.displayName')}</span><input required maxlength="100" bind:value={displayName} /></label>
				<fieldset class="roles" data-tour="users-roles">
					<legend class="label">{t('users.role')}</legend>
					{#each ROLES as r (r)}
						<label class="choice"><input type="radio" name="role" value={r} bind:group={role} /><strong>{t(`role.${r}`)}</strong><span>{t(`users.roleHelp.${r}`)}</span></label>
					{/each}
				</fieldset>
				<label class="field"><span>{t('users.password')}</span><input type="password" autocomplete="new-password" required minlength="10" bind:value={password} /><span class="hint">{t('users.passwordHint')}</span></label>
				<button class="btn primary" type="submit" disabled={busy}>{t('users.create')}</button>
			</form>
		</div>
	{/if}
</div>

<style>
	.layout {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 360px;
		gap: 24px;
		align-items: start;
	}
	.list {
		padding: 6px 12px;
		overflow-x: auto;
	}
	.gap {
		display: block;
		height: 8px;
	}
	.table select {
		width: auto;
		min-height: 34px;
		padding: 4px 8px;
	}
	tr.locked td {
		color: var(--muted);
	}
	.table .chip {
		margin-left: 6px;
	}
	.reset-row td {
		padding-top: 4px;
		background: #f7f8f7;
	}
	.reset {
		display: grid;
		gap: 10px;
		max-width: 420px;
		padding: 8px 0 4px;
	}
	.create {
		display: grid;
		gap: 14px;
		padding: 20px 22px;
	}
	.roles {
		border: 0;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 8px;
	}
	@media (max-width: 1000px) {
		.layout {
			grid-template-columns: 1fr;
		}
	}
	/* Phones: each account becomes a short block (name, role, status, actions) instead of a table to scroll sideways. */
	@media (max-width: 640px) {
		.list {
			overflow-x: visible;
		}
		.table thead {
			display: none;
		}
		.table,
		.table tbody,
		.table tr,
		.table td {
			display: block;
		}
		.table tr {
			display: grid;
			gap: 8px;
			padding: 12px 0;
			border-bottom: 1px solid var(--rule);
		}
		.table tr:last-child {
			border-bottom: 0;
		}
		.table td {
			padding: 0;
			border: 0;
		}
		.reset-row td {
			padding: 8px 10px;
		}
	}
</style>
