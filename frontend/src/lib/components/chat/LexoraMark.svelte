<script lang="ts">
	// The Lexora mark beside each answer: the same drawing as the brand in the top bar, at avatar size.
	let { size = 26 }: { size?: number } = $props();
</script>

<svg class="mark" viewBox="0 0 32 32" width={size} height={size} aria-hidden="true"
	><rect width="32" height="32" rx="7" fill="#2a2d30" /><rect x="7" y="20" width="18" height="5" rx="1" fill="#ffe36e" /><path
		d="M11 7v15h11"
		fill="none"
		stroke="#fff"
		stroke-width="3"
		stroke-linecap="square"
	/></svg
>

<style>
	.mark {
		flex: none;
		display: block;
	}
</style>
