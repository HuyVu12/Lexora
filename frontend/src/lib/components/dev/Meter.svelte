<script lang="ts">
	// A ratio against a limit: the fill carries severity (accent, then warning from 80%, then critical when used up),
	// the track is a lighter step of the same colour so the state reads across the whole bar. Transform only.
	let { used, limit, label }: { used: number; limit: number; label: string } = $props();

	const share = $derived(limit > 0 ? Math.min(1, used / limit) : 1);
	const tone = $derived(used >= limit ? 'bad' : share >= 0.8 ? 'warn' : 'ok');
</script>

<span class="meter {tone}" role="meter" aria-valuemin={0} aria-valuemax={limit} aria-valuenow={Math.min(used, limit)} aria-label={label}>
	<span class="fill" style:transform="scaleX({share})"></span>
</span>

<style>
	.meter {
		display: block;
		height: 6px;
		border-radius: 999px;
		overflow: hidden;
		background: color-mix(in srgb, var(--flag) 14%, white);
	}
	.fill {
		display: block;
		height: 100%;
		border-radius: inherit;
		background: var(--flag);
		transform-origin: left center;
		transition: transform var(--dur-slow) var(--ease-out);
	}
	@starting-style {
		.fill {
			transform: scaleX(0);
		}
	}
	.warn {
		background: var(--attention-soft);
	}
	.warn .fill {
		background: #c47d0e;
	}
	.bad {
		background: var(--reject-soft);
	}
	.bad .fill {
		background: var(--reject);
	}
	@media (prefers-reduced-motion: reduce) {
		.fill {
			transition: none;
		}
	}
</style>
