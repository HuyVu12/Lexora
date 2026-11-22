<script lang="ts">
	// A tiny column chart for a stat tile: one column per day, today in the accent, the days before in a recessive
	// grey, a hairline baseline so empty days still read as zero. Each day has its own hover target and tooltip.
	let { days, values, label, tone = 'accent' }: { days: string[]; values: number[]; label: string; tone?: 'accent' | 'bad' | 'warn' } = $props();

	const W = 112;
	const H = 28;
	const top = $derived(Math.max(1, ...values));
	const slot = $derived(W / Math.max(1, values.length));
	const bar = $derived(Math.max(2, Math.min(6, slot - 2)));
	const short = (day: string) => `${day.slice(8, 10)}/${day.slice(5, 7)}`;
	const height = (v: number) => (v > 0 ? Math.max(2, (H - 2) * (v / top)) : 0);
</script>

<svg class="spark {tone}" viewBox="0 0 {W} {H}" width={W} height={H} preserveAspectRatio="none" role="img" aria-label={label}>
	<line class="base" x1="0" x2={W} y1={H - 0.5} y2={H - 0.5} />
	{#each values as v, i (days[i] ?? i)}
		<g>
			<title>{short(days[i] ?? '')}: {v.toLocaleString('vi-VN')}</title>
			<rect class="hit" x={slot * i} y="0" width={slot} height={H} />
			{#if v > 0}
				<rect class="col" class:now={i === values.length - 1} x={slot * i + (slot - bar) / 2} y={H - 1 - height(v)} width={bar} height={height(v)} rx="1" />
			{/if}
		</g>
	{/each}
</svg>

<style>
	.spark {
		display: block;
		overflow: visible;
	}
	.base {
		stroke: var(--rule);
		stroke-width: 1;
	}
	.hit {
		fill: transparent;
	}
	.col {
		fill: var(--rule-strong);
	}
	g:hover .col {
		fill: var(--muted);
	}
	.accent .now {
		fill: var(--flag);
	}
	.bad .now {
		fill: var(--reject);
	}
	.warn .now {
		fill: var(--attention);
	}
</style>
