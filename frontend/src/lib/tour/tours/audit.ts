import type { Tour } from '../types.js';
import { firstOf } from './routes.js';

const page = /^\/research\/audit\/[^/]+$/;
const at = { page, route: firstOf(page, '/api/audit', 'sets', (id) => `/research/audit/${id}`) };

/**
 * The blinded check of extracted norms, following docs/guides/huong-dan-kiem-tra-quy-pham.md. Choosing a
 * label only marks the form; saving is pointed at, never pressed.
 */
export const auditTour: Tour = {
	id: 'audit',
	version: 1,
	title: 'tour.audit.name',
	summary: 'tour.audit.summary',
	roles: ['admin', 'reviewer'],
	guides: [],
	steps: [
		{ id: 'intro', title: 'tour.audit.intro.title', body: 'tour.audit.intro.body', missing: 'tour.audit.intro.missing', ...at },
		{ id: 'blind', target: 'audit-blind', title: 'tour.audit.blind.title', body: 'tour.audit.blind.body', ...at },
		{ id: 'rail', target: 'item-rail', title: 'tour.audit.rail.title', body: 'tour.audit.rail.body', ...at },
		{ id: 'unit', target: 'audit-unit', title: 'tour.audit.unit.title', body: 'tour.audit.unit.body', missing: 'tour.audit.unit.missing', ...at },
		{ id: 'norm', target: 'audit-norm', title: 'tour.audit.norm.title', body: 'tour.audit.norm.body', optional: true, ...at },
		{
			id: 'label',
			target: 'audit-labels',
			title: 'tour.audit.label.title',
			body: 'tour.audit.label.body',
			example: 'tour.audit.label.example',
			wait: { kind: 'change' },
			hint: 'tour.audit.label.hint',
			missing: 'tour.audit.unit.missing',
			placement: 'left',
			...at
		},
		{ id: 'note', target: 'audit-note', title: 'tour.audit.note.title', body: 'tour.audit.note.body', optional: true, ...at },
		{ id: 'save', target: 'audit-save', title: 'tour.audit.save.title', body: 'tour.audit.save.body', placement: 'top', optional: true, ...at },
		{ id: 'score', target: 'audit-score', title: 'tour.audit.score.title', body: 'tour.audit.score.body', optional: true, ...at },
		{ id: 'done', title: 'tour.audit.done.title', body: 'tour.audit.done.body' }
	]
};
