<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import { api } from '#lib/api.js';
	import { t, formatDay } from '#lib/i18n/index.svelte.js';
	import { session } from '#lib/session.svelte.js';
	import { notify, act } from '#lib/toast.svelte.js';
	import type { Account, Role } from '#lib/types.js';

	const ROLES: Role[] = ['reader', 'reviewer', 'admin'];
	let accounts = $state<Account[]>([]);
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
				<p class="lead">{t('users.lead')}</p>
			</div>
		</header>
		<div class="layout">
			<section class="sheet list">
				<table class="table">
					<thead>
						<tr><th scope="col">{t('users.username')}</th><th scope="col">{t('users.role')}</th><th scope="col">{t('users.status')}</th><th scope="col">{t('users.actions')}</th></tr>
					</thead>
					<tbody>
						{#each accounts as a (a.id)}
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
										<button type="button" class="btn quiet small" onclick={() => (resetFor = a)}>{t('users.reset')}</button>
									</div>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
				{#if resetFor}
					<form class="reset" onsubmit={reset}>
						<label class="field"><span>{t('users.newPassword', { name: resetFor.username })}</span>
							<input type="password" autocomplete="new-password" minlength="10" required bind:value={newPassword} /><span class="hint">{t('users.passwordHint')}</span>
						</label>
						<div class="row"><button class="btn primary small" type="submit">{t('users.reset')}</button><button class="btn quiet small" type="button" onclick={() => (resetFor = null)}>{t('common.cancel')}</button></div>
					</form>
				{/if}
			</section>
			<form class="panel create" onsubmit={create}>
				<h2 class="heading">{t('users.create')}</h2>
				<label class="field"><span>{t('users.username')}</span><input autocomplete="off" required minlength="3" maxlength="64" pattern="[A-Za-z0-9._\-]+" bind:value={username} /></label>
				<label class="field"><span>{t('users.displayName')}</span><input required maxlength="100" bind:value={displayName} /></label>
				<fieldset class="roles">
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
		padding: 8px 12px;
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
	.reset {
		display: grid;
		gap: 10px;
		padding: 16px 12px 12px;
		border-top: 1px dashed var(--rule-strong);
		max-width: 420px;
	}
	.create {
		display: grid;
		gap: 14px;
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
</style>
