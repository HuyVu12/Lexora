<script lang="ts">
	import { mount, unmount, tick } from 'svelte';
	import Icon from './Icon.svelte';
	import GuideButton from './GuideButton.svelte';
	import { t } from '#lib/i18n/index.svelte.js';
	import { guide } from '#lib/guide.svelte.js';
	import { animate, flip, reducedMotion, DUR, EASE } from '#lib/motion.js';
	import type { MessageKey } from '#lib/i18n/vi.js';

	// The page guide: open on the first visit to a page, remembered per page on this machine. It has no visible
	// heading (the page title sits right above it); it opens straight on the purpose line and closes with an x.
	// Closed, it folds into a small "?" button beside the page title (mounted into the page's h1), and reopens
	// out of that button. Strings are `guide.<name>.page`, `.purpose`, `.<n>` and `.<n>.d` for each step, and
	// `.note` when `note` is set; tests/test_guides.py fails when a page uses a name whose strings are missing.
	// Steps are numbered like the StepTag badges on the page sections, which show only while the guide is open.
	let { name, steps: count = 0, note = false }: { name: string; steps?: number; note?: boolean } = $props();

	const key = (suffix: string) => `guide.${name}.${suffix}` as MessageKey;
	const pageName = $derived(key('page'));
	const purpose = $derived(key('purpose'));
	const steps = $derived(Array.from({ length: count }, (_, i) => [key(String(i + 1)), key(`${i + 1}.d`)] as [MessageKey, MessageKey]));
	const storageKey = $derived(`lexora-guide-${name}`);
	const bodyId = $derived(`guide-body-${name}`);

	function stored(): boolean {
		try {
			return localStorage.getItem(`lexora-guide-${name}`) !== 'closed';
		} catch {
			return true;
		}
	}
	// Read before the first render, so a closed guide never flashes open.
	let open = $state(stored());
	let section = $state<HTMLElement | null>(null);
	let panel = $state<HTMLElement | null>(null);
	let title = $state<HTMLElement | null>(null);
	let busy = false;

	$effect(() => {
		guide.open = open;
	});

	// The "?" lives inside the page's h1. Mounting it as its own small root keeps the heading's text intact.
	const buttonProps = $state({ open: true, label: '', hint: '', controls: '', ontoggle: () => toggle() });
	$effect(() => {
		buttonProps.open = open;
		buttonProps.label = t('guide.what');
		buttonProps.hint = open ? t('guide.hide') : t('guide.show');
		buttonProps.controls = bodyId;
	});
	$effect(() => {
		if (!section) return;
		let scope: HTMLElement | null = section.parentElement;
		let heading: HTMLElement | null = null;
		while (scope && !heading) {
			heading = scope.querySelector<HTMLElement>('h1');
			scope = scope.parentElement;
		}
		if (!heading) return;
		title = heading;
		const button = mount(GuideButton, { target: heading, props: buttonProps });
		return () => {
			unmount(button);
			title = null;
		};
	});

	function remember(value: boolean) {
		try {
			localStorage.setItem(storageKey, value ? 'open' : 'closed');
		} catch {
			// Private mode: the choice lasts for this page view only.
		}
	}

	/** Where the panel would sit if it were shrunk onto the "?" button, as a transform from its own box. */
	function towardsButton(box: DOMRect): string | null {
		const button = title?.querySelector('.guide-q');
		if (!button) return null;
		const b = button.getBoundingClientRect();
		return `translate(${b.left - box.left}px, ${b.top - box.top}px) scale(${Math.max(0.08, b.width / box.width)}, ${Math.max(0.08, b.height / box.height)})`;
	}

	async function toggle() {
		if (busy) return;
		busy = true;
		const next = !open;
		remember(next);
		const followers = section?.parentElement ? [...section.parentElement.children].slice([...section.parentElement.children].indexOf(section) + 1) : [];
		try {
			if (next) {
				await flip(followers, async () => {
					open = true;
					await tick();
				});
				if (panel && !reducedMotion()) {
					const to = towardsButton(panel.getBoundingClientRect());
					animate(panel, {
						transform: [to ?? 'translateY(-6px) scale(0.98)', 'none'],
						opacity: [0, 1],
						duration: DUR.slow,
						ease: EASE.out
					});
				}
			} else {
				if (panel && !reducedMotion()) {
					const to = towardsButton(panel.getBoundingClientRect());
					const leaving = animate(panel, {
						transform: ['none', to ?? 'translateY(-6px) scale(0.98)'],
						opacity: { from: 1, to: 0, ease: EASE.out, duration: DUR.base - 40 },
						duration: DUR.base,
						ease: EASE.inOut
					});
					if (leaving) {
						await leaving;
						panel.style.visibility = 'hidden';
					}
				}
				await flip(followers, async () => {
					open = false;
					await tick();
				});
				const button = title?.querySelector('.guide-q');
				if (button) animate(button, { transform: ['scale(1)', 'scale(1.18)', 'scale(1)'], duration: DUR.slow, ease: EASE.out });
			}
		} finally {
			busy = false;
		}
	}
</script>

<section class="guide" class:open class:inline={!title} bind:this={section} aria-labelledby={open ? `guide-${name}` : undefined}>
	{#if !title && !open}
		<!-- No page title to sit beside: the guide folds into one line instead. -->
		<button type="button" class="btn quiet small reopen" aria-expanded="false" aria-controls={bodyId} onclick={toggle}>
			<Icon name="help" size={16} />{t('guide.what')} <span class="muted">{t(pageName)}</span>
		</button>
	{/if}
	{#if open}
		<div class="panel" id={bodyId} bind:this={panel}>
			<h2 id="guide-{name}" class="visually-hidden">{t('guide.what')}: {t(pageName)}</h2>
			<div class="head">
				<p class="purpose">{t(purpose)}</p>
				<button type="button" class="btn quiet small close" aria-expanded="true" aria-controls={bodyId} title={t('guide.hide')} onclick={toggle}>
					<Icon name="x" size={16} /><span class="visually-hidden">{t('guide.hide')}</span>
				</button>
			</div>
			{#if steps.length}
				<ol class="steps" style:--n={steps.length} class:many={steps.length > 3}>
					{#each steps as [stepTitle, detail], i (stepTitle)}
						<li>
							<span class="n" aria-hidden="true">{i + 1}</span>
							<span class="text"><strong>{t(stepTitle)}</strong><span class="detail">{t(detail)}</span></span>
						</li>
					{/each}
				</ol>
			{/if}
			{#if note}<p class="small muted note">{t(key('note'))}</p>{/if}
		</div>
	{/if}
</section>

<style>
	.guide:not(.open):not(.inline) {
		display: none;
	}
	.guide {
		margin: 0 0 var(--space-6);
	}
	.guide.inline:not(.open) {
		margin-bottom: var(--space-4);
	}
	.reopen {
		margin-left: -10px;
		color: var(--ink-2);
	}
	.reopen :global(svg) {
		color: var(--flag);
	}
	.panel {
		display: grid;
		gap: 10px;
		padding: 14px 18px 16px;
		background: #f3f6fd;
		border: 1px solid #d5e0f5;
		border-radius: var(--r-panel);
		transform-origin: 0 0;
		container: guide / inline-size;
	}
	.head {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 12px;
	}
	.close {
		flex: none;
		width: 30px;
		min-height: 30px;
		padding: 0;
		margin: -4px -8px 0 0;
		color: var(--muted);
	}
	.close:hover {
		color: var(--ink);
		background: rgb(47 95 196 / 0.08);
	}
	.purpose {
		max-width: 96ch;
		color: var(--ink-2);
	}
	.steps {
		list-style: none;
		margin: 2px 0 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(var(--n), minmax(0, 1fr));
		gap: 10px 24px;
	}
	/* Columns follow the steps and the room the panel has: never a lone step on its own row. */
	@container guide (max-width: 980px) {
		.steps.many {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@container guide (max-width: 620px) {
		.steps,
		.steps.many {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	.steps li {
		display: grid;
		grid-template-columns: 20px minmax(0, 1fr);
		gap: 10px;
		align-items: start;
	}
	.n {
		display: inline-grid;
		place-items: center;
		width: 20px;
		height: 20px;
		margin-top: 1px;
		border-radius: 50%;
		border: 1.5px solid var(--flag);
		color: var(--flag);
		font-size: 11.5px;
		font-weight: 700;
		line-height: 1;
	}
	.text {
		display: grid;
		gap: 1px;
		font-size: 14px;
		line-height: 1.5;
	}
	.text strong {
		font-weight: 600;
	}
	.detail {
		color: var(--muted);
		font-size: 13.5px;
	}
</style>
