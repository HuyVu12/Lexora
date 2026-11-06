import type { Unit } from './types.js';
import type { MessageKey } from './i18n/vi.js';

export class SelectionError extends Error {
	constructor(readonly key: MessageKey) {
		super(key);
	}
}

/** The current text selection as exact character offsets inside one statute unit, trimmed of whitespace. */
export function selectionAnchor(units: Map<string, Unit>): { unit_version_id: string; start: number; end: number } {
	const selection = getSelection();
	if (!selection || selection.rangeCount === 0 || selection.isCollapsed) throw new SelectionError('review.select.none');
	const range = selection.getRangeAt(0);
	const element = (node: Node) => (node.nodeType === Node.ELEMENT_NODE ? (node as Element) : node.parentElement);
	const startEl = element(range.startContainer)?.closest<HTMLElement>('[data-uv]');
	const endEl = element(range.endContainer)?.closest<HTMLElement>('[data-uv]');
	if (!startEl || startEl !== endEl) throw new SelectionError('review.select.cross');
	const unit = units.get(startEl.dataset.uv!);
	if (!unit) throw new SelectionError('review.select.cross');
	const offset = (node: Node, at: number) => {
		const r = document.createRange();
		r.setStart(startEl, 0);
		r.setEnd(node, at);
		return r.toString().length;
	};
	let start = offset(range.startContainer, range.startOffset);
	let end = offset(range.endContainer, range.endOffset);
	while (start < end && /\s/.test(unit.text[start])) start++;
	while (end > start && /\s/.test(unit.text[end - 1])) end--;
	if (start >= end) throw new SelectionError('review.select.blank');
	return { unit_version_id: unit.unit_version_id, start, end };
}
