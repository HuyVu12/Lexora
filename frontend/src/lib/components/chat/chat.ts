/**
 * Helpers shared by the chat components: recency groups for the sidebar, citation numbers, the plain-text copy
 * of an answer, and a small attachment that closes a popover on an outside press or Escape.
 */
import type { Attachment } from 'svelte/attachments';
import type { TransitionConfig } from 'svelte/transition';
import { t, unitLabel } from '#lib/i18n/index.svelte.js';
import { reducedMotion, DUR } from '#lib/motion.js';
import type { Citation, Turn } from '#lib/types.js';

export type Group = 'today' | 'week' | 'older';
export const GROUPS: Group[] = ['today', 'week', 'older'];

/** "Hôm nay" is the local calendar day; "7 ngày qua" the six days before it. */
export function groupOf(iso: string, now = new Date()): Group {
	const day = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
	const at = new Date(iso).getTime();
	if (at >= day) return 'today';
	if (at >= day - 6 * 86_400_000) return 'week';
	return 'older';
}

/** Citations are shown as [1], [2] in their order in the turn, whatever their stored IDs. */
export function citationNumber(turn: Turn, id: string): number {
	return turn.citations.findIndex((c) => c.id === id) + 1;
}

/** "Bộ luật Lao động 2019, Điều 26, khoản 1 (Kho: Kho A)" */
export function sourceLine(c: Citation): string {
	const where = unitLabel(c.evidence.unit_id);
	const kbs = c.sources.map((s) => s.kb_name).filter(Boolean).join(', ');
	return `${c.title}${where ? `, ${where}` : ''}${kbs ? ` (${t('chat.inKb', { names: kbs })})` : ''}`;
}

/** The answer as plain text for the clipboard: question, answer (statements or quotes) and numbered sources. */
export function plainAnswer(turn: Turn): string {
	const lines = [`${t('chat.question')}: ${turn.question}`, ''];
	if (turn.statements.length) {
		for (const s of turn.statements) lines.push(`${s.text} ${s.citation_ids.map((id) => `[${citationNumber(turn, id)}]`).join('')}`.trim());
	} else if (turn.citations.length) {
		turn.citations.forEach((c, i) => lines.push(`[${i + 1}] “${c.evidence.quote.trim()}”`));
	} else {
		lines.push(t('chat.noEvidence.title'));
	}
	if (turn.citations.length) {
		lines.push('', `${t('chat.sources')}:`);
		turn.citations.forEach((c, i) => lines.push(`[${i + 1}] ${sourceLine(c)}`));
	}
	lines.push('', t('chat.disclaimer'));
	return lines.join('\n');
}

/** Attachment: call `close` when the pointer goes down outside the node (and outside `keep`) or Escape is pressed. */
export function dismiss(close: () => void, keep?: () => Element | null | undefined): Attachment<HTMLElement> {
	return (node) => {
		const press = (event: PointerEvent) => {
			const target = event.target as Node;
			if (node.contains(target) || keep?.()?.contains(target)) return;
			close();
		};
		const key = (event: KeyboardEvent) => {
			if (event.key !== 'Escape') return;
			event.stopPropagation();
			close();
		};
		document.addEventListener('pointerdown', press, true);
		node.addEventListener('keydown', key);
		return () => {
			document.removeEventListener('pointerdown', press, true);
			node.removeEventListener('keydown', key);
		};
	};
}

/** Arrow keys move between the items of a menu; Home and End jump to the ends. */
export function menuKeys(event: KeyboardEvent, root: HTMLElement | null) {
	if (!root || !['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
	const items = [...root.querySelectorAll<HTMLElement>('[role^="menuitem"]:not([disabled]), input:not([disabled])')];
	if (!items.length) return;
	event.preventDefault();
	const at = items.indexOf(document.activeElement as HTMLElement);
	const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 : (at + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
	items[next].focus();
}

/** Svelte transition: a panel sliding in from an edge (x or y in px), with a fade. Exits are quicker. */
export function slideIn(_node: Element, { x = 0, y = 0, duration = DUR.slow }: { x?: number; y?: number; duration?: number } = {}): TransitionConfig {
	if (reducedMotion()) return { duration: 0 };
	return {
		duration,
		easing: (p) => 1 - Math.pow(1 - p, 4),
		css: (p, u) => `opacity: ${Math.min(1, p * 1.6)}; transform: translate(${u * x}px, ${u * y}px);`
	};
}

/** True where a fine pointer is the main input: focusing the composer there never pops a phone keyboard open. */
export function finePointer(): boolean {
	return typeof window !== 'undefined' && !!window.matchMedia?.('(pointer: fine)').matches;
}
