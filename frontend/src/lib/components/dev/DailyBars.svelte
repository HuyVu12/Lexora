<script lang="ts">
	// Stacked daily bars on one shared scale: a faint grid, round-number ticks, one tooltip per bar.
	type Series = { key: string; label: string; color: string; values: number[] };
	let { days, series, label }: { days: string[]; series: Series[]; label: string } = $props();

	const W = 640;
	const H = 180;
	const pad = { top: 10, right: 8, bottom: 24, left: 34 };
	const totals = $derived(days.map((_, i) => series.reduce((sum, s) => sum + (s.values[i] ?? 0), 0)));
	const top = $derived(niceMax(Math.max(1, ...totals)));
	const ticks = $derived([0, top / 2, top]);
	const slot = $derived((W - pad.left - pad.right) / Math.max(1, days.length));
	const barWidth = $derived(Math.max(3, Math.min(28, slot * 0.66)));
	const y = (v: number) => pad.top + (H - pad.top - pad.bottom) * (1 - v / top);
	const every = $derived(Math.ceil(days.length / 7));
	const short = (day: string) => `${day.slice(8, 10)}/${day.slice(5, 7)}`;

	function niceMax(value: number) {
		const step = 10 ** Math.floor(Math.log10(value));
		for (const m of [1, 2, 4, 5, 10]) if (m * step >= value) return Math.max(2, m * step);
		return 10 * step;
	}
	function stack(i: number) {
		let base = 0;
		return series.map((s) => {
			const v = s.values[i] ?? 0;
			const part = { s, v, from: base, to: base + v };
			base += v;
			return part;
		});
	}
</script>

<figure class="chart">
	<svg viewBox="0 0 {W} {H}" role="img" aria-label={label}>
		{#each ticks as tick (tick)}
			<line class="grid" x1={pad.left} x2={W - pad.right} y1={y(tick)} y2={y(tick)} />
			<text class="tick" x={pad.left - 6} y={y(tick) + 4} text-anchor="end">{Number.isInteger(tick) ? tick : tick.toFixed(1)}</text>
		{/each}
		{#each days as day, i (day)}
			{@const x = pad.left + slot * i + (slot - barWidth) / 2}
			<g>
				<title>{short(day)}: {series.map((s) => `${s.label} ${s.values[i] ?? 0}`).join(', ')}</title>
				<rect class="hit" x={pad.left + slot * i} y={pad.top} width={slot} height={H - pad.top - pad.bottom} />
				{#each stack(i) as part (part.s.key)}
					{#if part.v > 0}
						<rect x={x} y={y(part.to)} width={barWidth} height={Math.max(1, y(part.from) - y(part.to))} fill={part.s.color} rx="1.5" />
					{/if}
				{/each}
				{#if (days.length - 1 - i) % every === 0}
					<text class="tick" x={x + barWidth / 2} y={H - 6} text-anchor="middle">{short(day)}</text>
				{/if}
			</g>
		{/each}
	</svg>
	<figcaption class="legend">
		{#each series as s (s.key)}
			<span><i style="background:{s.color}"></i>{s.label} <strong>{s.values.reduce((a, b) => a + b, 0)}</strong></span>
		{/each}
	</figcaption>
</figure>

<style>
	.chart {
		margin: 0;
		display: grid;
		gap: 8px;
	}
	svg {
		width: 100%;
		height: auto;
		overflow: visible;
	}
	.grid {
		stroke: var(--rule);
		stroke-width: 1;
		vector-effect: non-scaling-stroke;
	}
	.tick {
		fill: var(--muted);
		font-size: 11px;
	}
	.hit {
		fill: transparent;
	}
	g:hover .hit {
		fill: var(--desk);
		opacity: 0.6;
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 4px 18px;
		font-size: 13px;
		color: var(--ink-2);
	}
	.legend i {
		display: inline-block;
		width: 10px;
		height: 10px;
		border-radius: 2px;
		margin-right: 6px;
	}
</style>
