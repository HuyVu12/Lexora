<script lang="ts">
	import DailyBars from './DailyBars.svelte';
	import Term from '#lib/components/Term.svelte';
	import { t } from '#lib/i18n/index.svelte.js';
	import type { DevUsage } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	let { data }: { data: DevUsage } = $props();

	const pct = (v: number | null) => (v === null ? '-' : `${(v * 100).toFixed(1)}%`);
	const ms = (v: number | null) => (v === null ? '-' : v < 1000 ? `${v} ms` : `${(v / 1000).toFixed(1)} s`);
	const days = $derived(data.daily.map((d) => d.day));
	const ROLES = ['admin', 'reviewer', 'reader', 'dev'];
	const logins = $derived([
		{ key: 'ok', label: t('dev.usage.loginOk'), color: 'var(--graphite)', values: data.daily.map((d) => d.login_ok) },
		{ key: 'refused', label: t('dev.usage.loginRefused'), color: 'var(--attention)', values: data.daily.map((d) => d.login_refused) },
		{ key: 'locked', label: t('dev.usage.loginLocked'), color: 'var(--reject)', values: data.daily.map((d) => d.login_locked) }
	]);
	const questions = $derived([{ key: 'q', label: t('dev.usage.questions'), color: 'var(--flag)', values: data.daily.map((d) => d.questions) }]);
	const statusLabel = (s: string) => t(`dev.chatStatus.${s}` as MessageKey) ?? s;
</script>

<div class="dev-tiles">
	<div class="dev-tile"><span class="label">{t('dev.usage.sessions')}</span><strong>{data.active_sessions}</strong><span class="small muted">{t('dev.usage.sessionsNote')}</span></div>
	<div class="dev-tile"><span class="label">{t('dev.usage.questions')}</span><strong>{data.questions}</strong><span class="small muted">{t('dev.usage.inDays', { days: data.days })}</span></div>
	<div class="dev-tile" class:warn={(data.no_evidence_rate ?? 0) > 0.3}>
		<span class="label"><Term key="no_evidence_rate">{t('dev.usage.noEvidence')}</Term></span><strong>{pct(data.no_evidence_rate)}</strong>
		<span class="small muted">{t('dev.usage.citations', { n: data.citations_mean === null ? '-' : data.citations_mean.toFixed(1) })}</span>
	</div>
	<div class="dev-tile"><span class="label">{t('dev.usage.latency')}</span><strong>{ms(data.p50_ms)}</strong><span class="small muted">p95 {ms(data.p95_ms)}</span></div>
</div>

<div class="dev-two">
	<section class="panel" aria-labelledby="questions-chart">
		<h2 class="heading" id="questions-chart">{t('dev.usage.questionsChart')}</h2>
		<DailyBars {days} series={questions} label={t('dev.usage.questionsChart')} />
	</section>
	<section class="panel" aria-labelledby="logins-chart">
		<h2 class="heading" id="logins-chart">{t('dev.usage.loginsChart')}</h2>
		<DailyBars {days} series={logins} label={t('dev.usage.loginsChart')} />
	</section>
</div>

<div class="dev-two">
	<section class="panel" aria-labelledby="answers-heading">
		<h2 class="heading" id="answers-heading">{t('dev.usage.answers')}</h2>
		{#if data.questions}
			<ul class="dev-list">
				<li><span>{t('dev.usage.extractive')}</span><strong>{data.by_mode.extractive}</strong></li>
				<li><span>{t('dev.usage.llm')}</span><strong>{data.by_mode.llm}</strong></li>
				<li><span>{t('dev.usage.semantic')}</span><strong>{data.semantic}</strong></li>
				{#each Object.entries(data.status) as [status, n] (status)}<li><span class="muted">{statusLabel(status)}</span><strong>{n}</strong></li>{/each}
			</ul>
		{:else}
			<p class="small muted">{t('dev.usage.noQuestions')}</p>
		{/if}
	</section>
	<section class="panel" aria-labelledby="accounts-heading">
		<h2 class="heading" id="accounts-heading">{t('dev.usage.accounts')}</h2>
		<ul class="dev-list">
			{#each ROLES as role (role)}
				<li><span>{t(`role.${role}` as MessageKey)}</span><strong>{data.accounts[role] ?? 0}{#if data.accounts[`${role}_inactive`]}<span class="small muted"> {t('dev.usage.inactive', { n: data.accounts[`${role}_inactive`] })}</span>{/if}</strong></li>
			{/each}
		</ul>
		<p class="small muted">{t('dev.usage.privacy')}</p>
	</section>
</div>
