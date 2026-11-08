<script lang="ts">
	import { t, formatDate } from '#lib/i18n/index.svelte.js';
	import type { DevSystem, Feature } from '#lib/types.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	let { data }: { data: DevSystem } = $props();

	const FEATURES: Feature[] = ['chat', 'extraction', 'proposal', 'embedding'];
	const size = (bytes: number | null) => (bytes === null ? '-' : bytes > 1e6 ? `${(bytes / 1e6).toFixed(1)} MB` : `${(bytes / 1e3).toFixed(0)} KB`);
</script>

<div class="dev-two">
	<section class="panel" aria-labelledby="app-heading">
		<h2 class="heading" id="app-heading">{t('dev.sys.app')}</h2>
		<dl>
			<dt>{t('dev.sys.commit')}</dt><dd><code>{data.commit ?? '-'}</code></dd>
			<dt>{t('dev.sys.started')}</dt><dd>{formatDate(data.started_at)}</dd>
			<dt>{t('dev.sys.frontend')}</dt><dd>{data.frontend_built_at ? formatDate(data.frontend_built_at) : '-'}</dd>
			<dt>Python</dt><dd>{data.python}</dd>
			<dt>{t('dev.sys.platform')}</dt><dd>{data.platform}</dd>
			<dt>{t('dev.sys.store')}</dt><dd><code>{data.store.path}</code> <span class="muted">({size(data.store.bytes)})</span></dd>
			<dt>{t('dev.sys.experiments')}</dt><dd><code>{data.experiments_dir}</code></dd>
		</dl>
	</section>
	<section class="panel" aria-labelledby="flags-heading">
		<h2 class="heading" id="flags-heading">{t('dev.sys.flags')}</h2>
		<dl>
			{#each FEATURES as f (f)}
				{@const m = data.models[f]}
				<dt>{t(`dev.feature.${f}` as MessageKey)}</dt>
				<dd>{#if m}<code>{m.model}</code> <span class="muted">{m.provider}{m.max_calls ? ` · ${t('dev.sys.budget', { used: m.calls ?? 0, max: m.max_calls })}` : ''}</span>{:else}<span class="muted">{t('dev.notEnabled')}</span>{/if}</dd>
			{/each}
			<dt>vbpl.vn</dt><dd>{data.vbpl_enabled ? t('dev.on') : t('dev.off')}</dd>
			<dt>{t('dev.sys.catalog')}</dt><dd>{data.catalog ? t('dev.on') : t('dev.off')}</dd>
		</dl>
		<p class="small muted">{t('dev.sys.secrets')}</p>
	</section>
</div>

<style>
	dl {
		display: grid;
		grid-template-columns: minmax(130px, max-content) minmax(0, 1fr);
		gap: 8px 16px;
		margin: 0;
		font-size: 14px;
	}
	dt {
		color: var(--muted);
	}
	dd {
		margin: 0;
		overflow-wrap: anywhere;
	}
</style>
