<script lang="ts">
	import { mount, unmount } from 'svelte';
	import GuideButton from './GuideButton.svelte';
	import { t } from '#lib/i18n/index.svelte.js';
	import { session } from '#lib/session.svelte.js';
	import { toursFor } from '#lib/tour/tour.svelte.js';

	// The "?" for a page that has a step-by-step tour but no page guide: mounted into the page's h1 like the
	// guide's button, it starts the tour directly. `tour` is the tour id (lib/tour/tours); nothing shows when the
	// signed-in role cannot take it.
	let { tour }: { tour: string } = $props();

	let anchor = $state<HTMLElement | null>(null);
	const allowed = $derived(toursFor(session.account?.role ?? null).some((x) => x.id === tour));
	const buttonProps = $state({ open: false, label: '', hint: '', controls: '', tourId: null as string | null });
	$effect(() => {
		buttonProps.label = t('tour.menu.steps');
		buttonProps.hint = t('tour.menu.steps');
		buttonProps.tourId = tour;
	});
	$effect(() => {
		if (!anchor || !allowed) return;
		let scope: HTMLElement | null = anchor.parentElement;
		let heading: HTMLElement | null = null;
		while (scope && !heading) {
			heading = scope.querySelector<HTMLElement>('h1');
			scope = scope.parentElement;
		}
		if (!heading) return;
		const button = mount(GuideButton, { target: heading, props: buttonProps });
		return () => {
			unmount(button);
		};
	});
</script>

<span class="tour-help" bind:this={anchor} hidden></span>
