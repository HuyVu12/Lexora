import type { Tour } from '../types.js';
import { firstOf, onlyHere } from './routes.js';

const page = /^\/research\/questions\/[^/]+$/;
const at = { page, route: firstOf(page, '/api/question-sets', 'sets', (id) => `/research/questions/${id}`) };

/**
 * Labelling a question set, following docs/annotation-guidelines.md and docs/guides/huong-dan-gan-nhan.md.
 * The proposal mode, adding a question and saving are explained; the only waits are opening the labelling
 * tab and typing into the unit search, which change nothing that is stored.
 */
export const questionsTour: Tour = {
	id: 'questions',
	version: 1,
	title: 'tour.questions.name',
	summary: 'tour.questions.summary',
	roles: ['admin', 'reviewer'],
	guides: ['qset'],
	next: 'compare',
	steps: [
		{ id: 'intro', title: 'tour.questions.intro.title', body: 'tour.questions.intro.body', missing: 'tour.questions.intro.missing', ...at },
		{ id: 'mode', target: 'qs-mode', title: 'tour.questions.mode.title', body: 'tour.questions.mode.body', missing: 'tour.questions.mode.missing', ...at },
		{ id: 'rail', target: 'item-rail', title: 'tour.questions.rail.title', body: 'tour.questions.rail.body', ...at },
		{ id: 'add', target: 'tab-add', title: 'tour.questions.add.title', body: 'tour.questions.add.body', optional: true, ...at },
		{
			id: 'open',
			target: 'tab-label',
			title: 'tour.questions.open.title',
			body: 'tour.questions.open.body',
			wait: { kind: 'click' },
			hint: 'tour.questions.open.hint',
			advance: true,
			...at
		},
		{ id: 'type', target: 'qs-type', title: 'tour.questions.type.title', body: 'tour.questions.type.body', missing: 'tour.questions.type.missing', ...at },
		{ id: 'status', target: 'qs-status', title: 'tour.questions.status.title', body: 'tour.questions.status.body', optional: true, ...at },
		{
			id: 'search',
			target: 'qs-unit-search',
			title: 'tour.questions.search.title',
			body: 'tour.questions.search.body',
			example: 'tour.questions.search.example',
			demo: { kind: 'type' },
			wait: { kind: 'input', min: 3 },
			hint: 'tour.questions.search.hint',
			optional: true,
			...at
		},
		{ id: 'units', target: 'qs-unit-row', title: 'tour.questions.units.title', body: 'tour.questions.units.body', optional: true, ...at },
		{ id: 'save', target: 'qs-save', title: 'tour.questions.save.title', body: 'tour.questions.save.body', placement: 'top', optional: true, ...at },
		{ id: 'exchange', target: 'tab-exchange', title: 'tour.questions.exchange.title', body: 'tour.questions.exchange.body', optional: true, ...at },
		{ id: 'done', title: 'tour.questions.done.title', body: 'tour.questions.done.body' }
	]
};

const cmp = /^\/research\/questions\/[^/]+\/compare$/;
const onCompare = { page: cmp, route: onlyHere(cmp) };

/** The compare page of a question set: agreement, final labels, freezing. Everything is explained only. */
export const compareTour: Tour = {
	id: 'compare',
	version: 1,
	title: 'tour.compare.name',
	summary: 'tour.compare.summary',
	roles: ['admin', 'reviewer'],
	guides: ['compare'],
	steps: [
		{ id: 'intro', title: 'tour.compare.intro.title', body: 'tour.compare.intro.body', missing: 'tour.compare.intro.missing', ...onCompare },
		{ id: 'metrics', target: 'cmp-metrics', title: 'tour.compare.metrics.title', body: 'tour.compare.metrics.body', optional: true, ...onCompare },
		{ id: 'final', target: 'cmp-final', title: 'tour.compare.final.title', body: 'tour.compare.final.body', optional: true, ...onCompare },
		{ id: 'freeze', target: 'cmp-freeze', title: 'tour.compare.freeze.title', body: 'tour.compare.freeze.body', missing: 'tour.compare.freeze.missing', ...onCompare },
		{ id: 'done', title: 'tour.compare.done.title', body: 'tour.compare.done.body' }
	]
};
