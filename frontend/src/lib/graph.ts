import type { ElementDefinition } from 'cytoscape';
import { ROLE_CLASS, SLOT_ORDER } from './roles.js';

// The evidence-graph-v2 export (see src/legal_ai/kb/graph.py).
export interface GNode {
	id: string;
	kind: string;
	label: string;
	payload: Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
}
export interface GEdge {
	id: string;
	kind: string;
	source: string;
	target: string;
	evidence_ids?: string[];
	reviewer?: string;
	reason?: string;
}
export interface Graph {
	nodes: GNode[];
	edges: GEdge[];
	summary?: { synthetic?: boolean };
	graph_hash?: string;
}
export interface EvidencePayload {
	evidence_id: string;
	quote: string;
	start: number;
	end: number;
	unit_id: string;
	unit_version_id: string;
	normalized_sha256: string;
	document_id: string;
}

export class GraphIndex {
	readonly nodes: Map<string, GNode>;
	readonly evidence: Map<string, EvidencePayload>;
	readonly units: Map<string, GNode>;
	readonly norms: GNode[];

	constructor(readonly graph: Graph) {
		this.nodes = new Map(graph.nodes.map((n) => [n.id, n]));
		this.evidence = new Map(graph.nodes.filter((n) => n.kind === 'Evidence').map((n) => [n.payload.evidence_id, n.payload as EvidencePayload]));
		this.units = new Map(graph.nodes.filter((n) => n.kind === 'LegalUnit').map((n) => [n.payload.unit_version_id, n]));
		this.norms = graph.nodes
			.filter((n) => n.kind === 'NormClaim')
			.sort((a, b) => this.unitOf(a).localeCompare(this.unitOf(b), undefined, { numeric: true }) || a.id.localeCompare(b.id));
	}

	unitOf(norm: GNode): string {
		return this.units.get(norm.payload.source_unit_version_ids?.[0])?.payload.unit_id ?? '';
	}

	document(id: string): GNode | undefined {
		return this.graph.nodes.find((n) => n.kind === 'Document' && n.payload.document_id === id);
	}

	/** "Subject action object" from a norm's present slots, falling back to its label. */
	title(norm: GNode): string {
		const slots = norm.payload.slots ?? {};
		const part = (k: string) => (slots[k]?.state === 'present' ? slots[k].text : '');
		return [part('actor'), part('action'), part('object')].filter(Boolean).join(' ') || norm.label;
	}

	/** The norm-centred neighbourhood: its source units, its parts, and entity mentions linked by a reviewer. */
	neighbourhood(normId: string) {
		const own = this.graph.edges.filter((e) => e.source === normId && (e.kind.startsWith('HAS_') || e.kind === 'EXTRACTED_FROM'));
		const ownTargets = new Set(own.map((e) => e.target));
		const links = this.graph.edges.filter((e) => e.kind === 'REVIEWED_ENTITY_LINK' && (ownTargets.has(e.source) || ownTargets.has(e.target)));
		const sources = own.filter((e) => e.kind === 'EXTRACTED_FROM').map((e) => this.nodes.get(e.target)).filter(Boolean) as GNode[];
		const rank = (n: GNode) => (n.kind === 'Modality' ? -1 : SLOT_ORDER.indexOf(n.payload.slot_name) < 0 ? 99 : SLOT_ORDER.indexOf(n.payload.slot_name));
		const parts = own
			.filter((e) => e.kind !== 'EXTRACTED_FROM' && e.kind !== 'HAS_SCOPE' && e.kind !== 'HAS_REFERENCE_TEXT')
			.map((e) => this.nodes.get(e.target))
			.filter(Boolean)
			.sort((a, b) => rank(a!) - rank(b!)) as GNode[];
		const linked = links.map((e) => this.nodes.get(ownTargets.has(e.source) ? e.target : e.source)).filter((n) => n && !ownTargets.has(n.id)) as GNode[];
		return { own, links, sources, parts, linked };
	}
}

export function roleClass(node: GNode): string {
	if (node.kind === 'Modality') return 'modality';
	return ROLE_CLASS[node.payload?.slot_name] ?? 'hl-other';
}

const ellipsis = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

/** Elements for one norm: sources left, the norm centre, parts right (positions are preset; users may drag). */
export function normElements(index: GraphIndex, normId: string, labels: { norm: string; source: string; modality: string; role: (n: GNode) => string }): ElementDefinition[] {
	const norm = index.nodes.get(normId);
	if (!norm) return [];
	const { own, links, sources, parts, linked } = index.neighbourhood(normId);
	const rowH = 78;
	const height = Math.max(parts.length + (linked.length ? linked.length + 1 : 0), sources.length * 1.4, 1) * rowH;
	const els: ElementDefinition[] = [];
	els.push({
		group: 'nodes',
		data: { id: norm.id, label: ellipsis(index.title(norm), 70), kicker: labels.norm, kind: 'norm', decided: norm.payload.human_review ? 'yes' : 'no' },
		position: { x: 0, y: height / 2 },
		classes: 'norm'
	});
	sources.forEach((n, i) =>
		els.push({
			group: 'nodes',
			data: { id: n.id, label: ellipsis(n.label, 40), kicker: labels.source, kind: 'source' },
			position: { x: -250, y: height / 2 + (i - (sources.length - 1) / 2) * 96 },
			classes: 'source'
		})
	);
	parts.forEach((n, i) =>
		els.push({
			group: 'nodes',
			data: { id: n.id, label: ellipsis(n.kind === 'Modality' ? labels.role(n) : n.label, 40), kicker: n.kind === 'Modality' ? labels.modality : labels.role(n), kind: 'part' },
			position: { x: 250, y: rowH / 2 + i * rowH },
			classes: `part ${roleClass(n)}`
		})
	);
	linked.forEach((n, i) =>
		els.push({
			group: 'nodes',
			data: { id: n.id, label: ellipsis(n.label, 40), kicker: labels.role(n), kind: 'linked' },
			position: { x: 250, y: rowH / 2 + (parts.length + 1 + i) * rowH },
			classes: `part linked ${roleClass(n)}`
		})
	);
	const present = new Set(els.map((e) => e.data.id));
	for (const e of [...own, ...links]) {
		if (!present.has(e.source) || !present.has(e.target)) continue;
		els.push({ group: 'edges', data: { id: e.id, source: e.source, target: e.target, kind: e.kind }, classes: e.kind === 'REVIEWED_ENTITY_LINK' ? 'link' : e.kind === 'EXTRACTED_FROM' ? 'from' : 'has' });
	}
	return els;
}

/** Elements for the structure view: documents, articles, clauses and points as a left-to-right tree. */
export function structureElements(index: GraphIndex, kinds: { unit: (n: GNode) => string; document: string; norm: string }): ElementDefinition[] {
	const g = index.graph;
	const visible = g.nodes.filter((n) => n.kind === 'Document' || n.kind === 'LegalUnit' || n.kind === 'NormClaim');
	const ids = new Set(visible.map((n) => n.id));
	const primary = (n: GNode) => index.units.get(n.payload.source_unit_version_ids?.[0])?.id;
	const edges = g.edges.filter((e) => {
		if (!ids.has(e.source) || !ids.has(e.target)) return false;
		if (e.kind === 'EXTRACTED_FROM') return primary(index.nodes.get(e.source)!) === e.target; // only the clause the norm comes from
		return e.kind === 'PART_OF' || e.kind === 'REFERENCES';
	});
	const children = new Map<string, string[]>(visible.map((n) => [n.id, []]));
	for (const e of edges) {
		if (e.kind === 'PART_OF' || e.kind === 'EXTRACTED_FROM') children.get(e.target)?.push(e.source);
	}
	const order = (id: string) => {
		const n = index.nodes.get(id)!;
		return n.kind === 'NormClaim' ? `~${index.unitOf(n)}` : String(n.payload.unit_id ?? n.label);
	};
	for (const list of children.values()) list.sort((a, b) => order(a).localeCompare(order(b), undefined, { numeric: true }));
	const pos = new Map<string, { x: number; y: number }>();
	let y = 0;
	const place = (id: string, depth: number, seen: Set<string>) => {
		if (seen.has(id) || pos.has(id)) return;
		seen.add(id);
		pos.set(id, { x: depth * 205, y });
		y += 68;
		for (const child of children.get(id) ?? []) place(child, depth + 1, seen);
	};
	for (const doc of visible.filter((n) => n.kind === 'Document')) {
		place(doc.id, 0, new Set());
		y += 40;
	}
	for (const n of visible) if (!pos.has(n.id)) place(n.id, 0, new Set());
	const els: ElementDefinition[] = visible.map((n) => ({
		group: 'nodes' as const,
		data: {
			id: n.id,
			label: ellipsis(n.kind === 'NormClaim' ? index.title(n) : n.label, 44),
			kicker: n.kind === 'Document' ? kinds.document : n.kind === 'NormClaim' ? kinds.norm : kinds.unit(n),
			kind: n.kind
		},
		position: pos.get(n.id)!,
		classes: n.kind === 'Document' ? 'doc' : n.kind === 'NormClaim' ? 'norm small' : 'unit'
	}));
	for (const e of edges) els.push({ group: 'edges', data: { id: e.id, source: e.source, target: e.target, kind: e.kind }, classes: e.kind === 'REFERENCES' ? 'ref' : 'tree' });
	return els;
}

/** Every norm in the base, one row each: its source unit on the left, the norm, then its parts left to right.
 *  Reviewer-confirmed entity links join mentions across rows. */
export function allNormsElements(index: GraphIndex, norms: GNode[], labels: { norm: string; source: string; modality: string; role: (n: GNode) => string }): ElementDefinition[] {
	const els: ElementDefinition[] = [];
	const present = new Set<string>();
	const rowH = 96;
	const sourcesPlaced = new Map<string, number>();
	norms.forEach((norm, row) => {
		const y = row * rowH;
		const { own, sources, parts } = index.neighbourhood(norm.id);
		els.push({ group: 'nodes', data: { id: norm.id, label: ellipsis(index.title(norm), 54), kicker: labels.norm, kind: 'norm' }, position: { x: 0, y }, classes: 'norm compact' });
		present.add(norm.id);
		const source = sources.find((s) => s.payload.unit_version_id === norm.payload.source_unit_version_ids?.[0]) ?? sources[0];
		if (source && !present.has(source.id)) {
			els.push({ group: 'nodes', data: { id: source.id, label: ellipsis(source.label, 40), kicker: labels.source, kind: 'source' }, position: { x: -250, y }, classes: 'source' });
			present.add(source.id);
			sourcesPlaced.set(source.id, y);
		}
		parts.forEach((part, i) => {
			if (present.has(part.id)) return;
			els.push({
				group: 'nodes',
				data: { id: part.id, label: ellipsis(part.kind === 'Modality' ? labels.role(part) : part.label, 34), kicker: part.kind === 'Modality' ? labels.modality : labels.role(part), kind: 'part' },
				position: { x: 250 + i * 215, y },
				classes: `part ${roleClass(part)}`
			});
			present.add(part.id);
		});
		for (const e of own) {
			if (e.kind === 'EXTRACTED_FROM' && e.target !== source?.id) continue;
			if (present.has(e.source) && present.has(e.target)) {
				els.push({ group: 'edges', data: { id: e.id, source: e.source, target: e.target, kind: e.kind }, classes: e.kind === 'EXTRACTED_FROM' ? 'from' : 'has' });
			}
		}
	});
	for (const e of index.graph.edges) {
		if (e.kind === 'REVIEWED_ENTITY_LINK' && present.has(e.source) && present.has(e.target)) {
			els.push({ group: 'edges', data: { id: e.id, source: e.source, target: e.target, kind: e.kind }, classes: 'link' });
		}
	}
	return els;
}
