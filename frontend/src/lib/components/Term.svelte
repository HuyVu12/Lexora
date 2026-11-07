<script lang="ts">
	import type { Snippet } from 'svelte';
	import { entry } from '#lib/glossary.svelte.js';

	// A glossary word: GlossaryTip explains anything carrying data-term on hover, focus or tap.
	let { key, children, focusable = true }: { key: string; children?: Snippet; focusable?: boolean } = $props();
</script>

<!-- Keyboard users must reach the word to read its definition (WCAG 2.1.1), so it takes focus without being a control. -->
<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
<span class="term" data-term={key} tabindex={focusable ? 0 : undefined}
	>{#if children}{@render children()}{:else}{entry(key)?.term ?? key}{/if}</span
>
