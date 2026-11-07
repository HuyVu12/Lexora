<script lang="ts">
	import Icon from './Icon.svelte';
	import { t } from '#lib/i18n/index.svelte.js';
	import { guide } from '#lib/guide.svelte.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	// "What is this page?": open on the first visit, collapsible to one line, remembered per page on this machine.
	// Strings are `guide.<name>.page`, `.purpose`, `.<n>` and `.<n>.d` for each step, and `.note` when `note` is set;
	// tests/test_guides.py fails when a page uses a name whose strings are missing in vi.ts or en.ts.
	// Steps are numbered like the StepTag badges on the page sections.
	let { name, steps: count = 0, note = false }: { name: string; steps?: number; note?: boolean } = $props();

	const id = $derived(name);
	const key = (suffix: string) => `guide.${name}.${suffix}` as MessageKey;
	const page = $derived(key('page'));
	const purpose = $derived(key('purpose'));
	const steps = $derived(Array.from({ length: count }, (_, i) => [key(String(i + 1)), key(`${i + 1}.d`)] as [MessageKey, MessageKey]));
	const storageKey = $derived(`lexora-guide-${id}`);
	let open = $state(true);
	$effect(() => {
		try {
			open = localStorage.getItem(storageKey) !== 'closed';
		} catch {
			open = true;
		}
	});
	// The page's step badges follow the guide: hidden guide, hidden badges.
	$effect(() => {
		guide.open = open;
	});

	function toggle() {
		open = !open;
		try {
			localStorage.setItem(storageKey, open ? 'open' : 'closed');
		} catch {
			// Private mode: the choice lasts for this page view only.
		}
	}
</script>

<section class="guide" class:open aria-labelledby="guide-{id}">
	<div class="head">
		<Icon name="info" size={18} />
		<h2 id="guide-{id}" class="what">{t('guide.what')} <span class="page-name">{t(page)}</span></h2>
		<button type="button" class="btn quiet small" aria-expanded={open} aria-controls="guide-body-{id}" onclick={toggle}>
			{open ? t('guide.hide') : t('guide.show')}
		</button>
	</div>
	{#if open}
		<div class="body" id="guide-body-{id}">
			<p>{t(purpose)}</p>
			{#if steps.length}
				<ol class="steps">
					{#each steps as [title, detail], i (title)}
						<li>
							<span class="n" aria-hidden="true">{i + 1}</span>
							<span><strong>{t(title)}</strong><span class="detail">{t(detail)}</span></span>
						</li>
					{/each}
				</ol>
			{/if}
			{#if note}<p class="small muted note">{t(key('note'))}</p>{/if}
		</div>
	{/if}
</section>

<style>
	.guide {
		margin: 0 0 20px;
		padding: 10px 16px;
		background: #edf2fc;
		border: 1px solid #c9d7f3;
		border-radius: var(--r-panel);
		color: var(--ink);
	}
	.guide.open {
		padding: 14px 18px 16px;
	}
	.head {
		display: flex;
		align-items: center;
		gap: 10px;
		color: var(--flag);
	}
	.what {
		flex: 1;
		margin: 0;
		font-size: 15px;
		font-weight: 600;
		color: var(--ink);
	}
	.page-name {
		font-weight: 400;
		color: var(--ink-2);
	}
	.guide.open .page-name {
		display: none;
	}
	.body {
		display: grid;
		gap: 10px;
		margin-top: 8px;
		padding-left: 28px;
		max-width: 92ch;
	}
	.body p {
		margin: 0;
	}
	.steps {
		list-style: none;
		margin: 2px 0 0;
		padding: 0;
		display: grid;
		gap: 8px;
	}
	.steps li {
		display: grid;
		grid-template-columns: 24px minmax(0, 1fr);
		gap: 10px;
		align-items: start;
	}
	.n {
		display: inline-grid;
		place-items: center;
		width: 22px;
		height: 22px;
		border-radius: 50%;
		background: var(--flag);
		color: var(--paper);
		font-size: 12.5px;
		font-weight: 700;
		margin-top: 1px;
	}
	.steps strong {
		font-weight: 600;
		margin-right: 6px;
	}
	.detail {
		color: var(--ink-2);
	}
	@media (max-width: 640px) {
		.body {
			padding-left: 0;
		}
	}
</style>
