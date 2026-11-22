<script lang="ts">
	// A placeholder that holds the place of content still loading. Size it like the content it stands for,
	// so nothing moves when the data arrives. It stays invisible for the first 140 ms (fast answers never
	// flash grey) and is hidden from screen readers; the page announces loading once, not per block.
	let {
		width = '100%',
		height = '14px',
		lines = 1,
		radius = '4px',
		gap = '10px',
		last = '62%'
	}: {
		width?: string;
		height?: string;
		/** Text lines; the last one is shorter, like a real paragraph. */
		lines?: number;
		radius?: string;
		gap?: string;
		/** Width of the last line when `lines` > 1. */
		last?: string;
	} = $props();
</script>

{#if lines > 1}
	<span class="lines" style:gap aria-hidden="true">
		{#each { length: lines } as _, i (i)}
			<span class="skel" style:width={i === lines - 1 ? last : width} style:height style:border-radius={radius}></span>
		{/each}
	</span>
{:else}
	<span class="skel" style:width style:height style:border-radius={radius} aria-hidden="true"></span>
{/if}

<style>
	.lines {
		display: grid;
	}
</style>
