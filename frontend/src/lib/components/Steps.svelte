<script lang="ts">
	import { t } from '#lib/i18n/index.svelte.js';
	import Icon from './Icon.svelte';

	// Where the reviewer is in import, review, publish. Done steps carry a check; a thin rule joins the steps.
	let { current }: { current: 1 | 2 | 3 | 4 } = $props();
	const steps = ['steps.1', 'steps.2', 'steps.3'] as const;
</script>

<ol class="steps" aria-label={t('steps.label')}>
	{#each steps as key, i (key)}
		<li class:done={i + 1 < current} class:current={i + 1 === current} aria-current={i + 1 === current ? 'step' : undefined}>
			<span class="dot" aria-hidden="true">{#if i + 1 < current}<Icon name="check" size={13} />{:else}{i + 1}{/if}</span>{t(key)}
		</li>
	{/each}
</ol>

<style>
	.steps {
		display: flex;
		align-items: center;
		gap: 12px;
		list-style: none;
		margin: 0 0 var(--space-5);
		padding: 0;
		color: var(--muted);
		font-size: 13.5px;
		flex-wrap: wrap;
	}
	li {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	li + li::before {
		content: '';
		width: 28px;
		height: 1px;
		margin-right: 4px;
		background: var(--rule-strong);
	}
	li.done + li::before,
	li.done + li.done::before {
		background: var(--approve);
	}
	.dot {
		width: 22px;
		height: 22px;
		border-radius: 50%;
		display: grid;
		place-items: center;
		border: 1px solid var(--rule-strong);
		background: var(--paper);
		font-size: 12px;
		font-weight: 600;
	}
	.done {
		color: var(--ink-2);
	}
	.done .dot {
		background: var(--approve);
		border-color: var(--approve);
		color: #fff;
	}
	.current {
		color: var(--ink);
		font-weight: 600;
	}
	.current .dot {
		background: var(--graphite);
		border-color: var(--graphite);
		color: #fff;
		box-shadow: 0 0 0 3px rgb(42 45 48 / 0.12);
	}
	@media (max-width: 640px) {
		.steps {
			gap: 6px 16px;
		}
		li + li::before {
			display: none;
		}
	}
</style>
