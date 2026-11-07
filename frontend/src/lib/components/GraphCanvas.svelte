<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import cytoscape, { type Core, type ElementDefinition, type StylesheetJson } from 'cytoscape';
	import Icon from './Icon.svelte';
	import { t } from '#lib/i18n/index.svelte.js';

	// A Cytoscape canvas in the marked-up statute world: norms are white paper with graphite ink,
	// parts carry their role's highlighter colour, sources sit on the desk grey. The lists beside the
	// canvas are the keyboard path to every node; the canvas is a visual aid.
	let {
		elements,
		selected = null,
		label,
		layout = 'preset',
		focus = null,
		onselect
	}: {
		elements: ElementDefinition[];
		selected?: string | null;
		label: string;
		/** preset: centre on the norm; tree and rows: start at the top-left, where reading starts. */
		layout?: 'preset' | 'tree' | 'rows';
		/** Pan (without refitting) so this node is in view, e.g. when picked from the list. */
		focus?: string | null;
		onselect: (target: { group: 'nodes' | 'edges'; id: string }) => void;
	} = $props();

	let host = $state<HTMLDivElement | null>(null);
	let cy: Core | null = null;

	const HL: Record<string, string> = {
		'hl-actor': '#ffe36e', 'hl-action': '#b4ecbe', 'hl-object': '#cfe0ff', 'hl-party': '#ffc6da',
		'hl-condition': '#ffd8a3', 'hl-measure': '#c2efe8', 'hl-other': '#e4e6e6'
	};
	const sans = 'Be Vietnam Pro, system-ui, sans-serif';
	// Canvas font shorthand: a family name with a digit must be quoted or the whole font is ignored.
	const serif = "'Source Serif 4 Variable', Georgia, serif";

	const style: StylesheetJson = [
		{
			selector: 'node',
			style: {
				shape: 'round-rectangle', width: 200, height: 58, 'background-color': '#ffffff', 'border-width': 1, 'border-color': '#b6babb',
				label: (n: cytoscape.NodeSingular) => `${n.data('kicker') ?? ''}\n${n.data('label') ?? ''}`,
				'text-wrap': 'wrap', 'text-max-width': '178px', 'text-valign': 'center', 'text-halign': 'center', 'text-justification': 'left',
				'font-family': sans, 'font-size': 12.5, color: '#222426', 'line-height': 1.35
			}
		},
		{ selector: 'node.norm', style: { width: 240, height: 112, 'border-width': 1.6, 'border-color': '#222426', 'font-family': serif, 'font-size': 15, 'font-weight': 600, 'text-max-width': '214px' } },
		{ selector: 'node.norm.compact', style: { width: 240, height: 74, 'font-size': 13.5, 'text-max-width': '214px' } },
		{ selector: 'node.norm.small', style: { width: 200, height: 58, 'font-size': 12.5, 'font-weight': 400, 'font-family': sans, 'text-max-width': '178px', 'border-color': '#2f5fc4', 'border-style': 'dashed' } },
		{ selector: 'node.source', style: { 'background-color': '#e7e8e7', 'border-color': '#b6babb' } },
		{ selector: 'node.doc', style: { 'background-color': '#2a2d30', 'border-color': '#2a2d30', color: '#ffffff', 'font-weight': 600 } },
		{ selector: 'node.unit', style: { width: 200 } },
		...Object.entries(HL).map(([cls, color]) => ({ selector: `node.${cls}`, style: { 'background-color': color, 'border-color': 'rgba(0,0,0,0.14)' } })),
		{ selector: 'node.modality', style: { 'background-color': '#ffffff', 'border-color': '#3f4347', 'border-width': 1.5, shape: 'round-rectangle' } },
		{ selector: 'node.linked', style: { 'border-style': 'dashed', 'border-color': '#1f7342', 'border-width': 1.5 } },
		{ selector: 'node:selected', style: { 'border-width': 3, 'border-color': '#2f5fc4', 'underlay-color': '#2f5fc4', 'underlay-opacity': 0.12, 'underlay-padding': 6 } },
		{ selector: 'node.dim', style: { opacity: 0.35 } },
		{ selector: 'edge', style: { width: 1.4, 'line-color': '#b6babb', 'curve-style': 'unbundled-bezier', 'control-point-distances': 0, 'target-arrow-shape': 'none' } },
		{ selector: 'edge.tree', style: { 'curve-style': 'taxi', 'taxi-direction': 'horizontal', 'taxi-turn': 24 } },
		{ selector: 'edge.ref', style: { 'line-color': '#8a5300', 'line-style': 'dashed', width: 1.6, 'curve-style': 'bezier', 'target-arrow-shape': 'triangle', 'target-arrow-color': '#8a5300', 'arrow-scale': 0.8 } },
		{ selector: 'edge.link', style: { 'line-color': '#1f7342', 'line-style': 'dashed', width: 1.6, 'curve-style': 'bezier' } },
		{ selector: 'edge:selected', style: { 'line-color': '#2f5fc4', width: 3 } }
	];

	const reduce = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
	const READABLE = 0.9; // below this the 12.5px labels stop being legible

	function apply() {
		if (!cy) return;
		cy.batch(() => {
			cy!.elements().remove();
			cy!.add(elements);
		});
		cy.fit(undefined, 40);
		if (cy.zoom() > 1.1) cy.zoom(1.1);
		const floor = layout === 'tree' ? 0.8 : READABLE; // a whole document tree may sit a little smaller
		if (cy.zoom() < floor) {
			cy.zoom(floor);
			if (layout !== 'preset') {
				const box = cy.elements().boundingBox();
				cy.pan({ x: 40 - box.x1 * floor, y: 40 - box.y1 * floor });
			} else cy.center(cy.nodes('.norm').length ? cy.nodes('.norm') : cy.elements());
		} else cy.center();
		if (host) host.dataset.nodes = String(cy.nodes().length);
		record();
		mark();
	}

	/** Viewport and drawn bounds as data attributes, so the browser check sees what a user sees. */
	function record() {
		if (!host || !cy) return;
		const b = cy.elements().renderedBoundingBox();
		host.dataset.view = `${cy.zoom().toFixed(3)}:${cy.pan().x.toFixed(0)}:${cy.pan().y.toFixed(0)}`;
		host.dataset.bounds = `${b.x1.toFixed(0)}:${b.y1.toFixed(0)}:${b.x2.toFixed(0)}:${b.y2.toFixed(0)}`;
	}

	function mark() {
		if (!cy) return;
		cy.elements().unselect();
		if (selected) cy.getElementById(selected).select();
	}

	onMount(() => {
		let disposed = false;
		let observer: ResizeObserver | null = null;
		document.fonts.ready.then(() => {
			if (disposed || !host) return;
			cy = cytoscape({ container: host, style, elements: [], layout: { name: 'preset' }, minZoom: 0.25, maxZoom: 2.5, wheelSensitivity: 0.25, boxSelectionEnabled: false, autoungrabify: false });
			cy.on('tap', 'node', (e) => onselect({ group: 'nodes', id: e.target.id() }));
			cy.on('tap', 'edge', (e) => onselect({ group: 'edges', id: e.target.id() }));
			cy.on('viewport', record);
			apply();
			// The canvas changes size when side panels are shown or hidden, or the window resizes:
			// keep the same model point at the centre so nothing the reader was looking at moves away.
			let size = { w: host.clientWidth, h: host.clientHeight };
			observer = new ResizeObserver(() => {
				if (!cy || !host) return;
				const next = { w: host.clientWidth, h: host.clientHeight };
				if (next.w === size.w && next.h === size.h) return;
				const z = cy.zoom();
				const model = { x: (size.w / 2 - cy.pan().x) / z, y: (size.h / 2 - cy.pan().y) / z };
				size = next;
				cy.resize();
				cy.pan({ x: next.w / 2 - model.x * z, y: next.h / 2 - model.y * z });
			});
			observer.observe(host);
		});
		return () => {
			disposed = true;
			observer?.disconnect();
			cy?.destroy();
			cy = null;
		};
	});

	$effect(() => {
		void elements;
		untrack(apply); // apply reads `selected` and `layout`; selection alone must not refit the view
	});
	$effect(() => {
		void selected;
		untrack(mark);
	});
	$effect(() => {
		const id = focus;
		if (!id) return;
		untrack(() => {
			const node = cy?.getElementById(id);
			if (!cy || !node || node.empty()) return;
			if (reduce()) cy.center(node);
			else cy.animate({ center: { eles: node } }, { duration: 220, easing: 'ease-out' });
		});
	});
	const zoom = (factor: number) => {
		if (!cy) return;
		const level = Math.min(2.5, Math.max(0.25, cy.zoom() * factor));
		const center = { x: cy.width() / 2, y: cy.height() / 2 };
		if (reduce()) cy.zoom({ level, renderedPosition: center });
		else cy.animate({ zoom: { level, renderedPosition: center } }, { duration: 160, easing: 'ease-out' });
	};
	const fit = () => {
		if (!cy) return;
		if (reduce()) cy.fit(undefined, 40);
		else cy.animate({ fit: { eles: cy.elements(), padding: 40 } }, { duration: 220, easing: 'ease-out' });
	};
</script>

<div class="canvas-wrap">
	<div class="canvas" bind:this={host} role="img" aria-label={label} data-layout={layout}></div>
	<div class="tools" role="group" aria-label={t('graph.tools')}>
		<button type="button" class="btn small" aria-label={t('graph.zoomIn')} onclick={() => zoom(1.25)}><Icon name="plus" size={16} /></button>
		<button type="button" class="btn small" aria-label={t('graph.zoomOut')} onclick={() => zoom(0.8)}><Icon name="minus" size={16} /></button>
		<button type="button" class="btn small" onclick={fit}>{t('graph.fit')}</button>
	</div>
</div>

<style>
	.canvas-wrap {
		position: relative;
		height: 100%;
		min-height: 520px;
	}
	.canvas {
		position: absolute;
		inset: 0;
		background-color: var(--paper);
		background-image: radial-gradient(#dcdfdf 1px, transparent 1px);
		background-size: 22px 22px;
	}
	.tools {
		position: absolute;
		right: 12px;
		bottom: 12px;
		display: flex;
		gap: 6px;
		padding: 6px;
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: var(--r-panel);
		box-shadow: var(--shadow-sheet);
	}
	.tools .btn {
		min-width: 32px;
	}
</style>
