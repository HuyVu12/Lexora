import type { Tour } from '../types.js';
import { firstOf } from './routes.js';

const page = /^\/research\/gold\/[^/]+$/;
const at = { page, route: firstOf(page, '/api/gold', 'sets', (id) => `/research/gold/${id}`) };

/**
 * Gold extraction labelling on the sentence that is open, following docs/guides/huong-dan-gan-nhan-gold.md:
 * read the sentence with its lead, add a norm, choose the modality, select the exact words and press Điền.
 * Filling a field only changes the form on screen; saving and the exchange tab are pointed at, never pressed.
 */
export const goldTour: Tour = {
	id: 'gold',
	version: 1,
	title: 'tour.gold.name',
	summary: 'tour.gold.summary',
	area: 'research',
	alsoOn: /^\/research\/gold$/,
	roles: ['admin', 'reviewer'],
	guides: ['gold'],
	steps: [
		{ id: 'intro', title: 'tour.gold.intro.title', body: 'tour.gold.intro.body', missing: 'tour.gold.intro.missing', ...at },
		{ id: 'rail', target: 'item-rail', title: 'tour.gold.rail.title', body: 'tour.gold.rail.body', ...at },
		{ id: 'read', target: 'gold-item', title: 'tour.gold.read.title', body: 'tour.gold.read.body', missing: 'tour.gold.read.missing', ...at },
		{ id: 'noNorm', target: 'gold-no-norm', title: 'tour.gold.noNorm.title', body: 'tour.gold.noNorm.body', placement: 'top', optional: true, ...at },
		{
			id: 'add',
			target: 'gold-add-norm',
			title: 'tour.gold.add.title',
			body: 'tour.gold.add.body',
			wait: { kind: 'appear', selector: '[data-tour="gold-norm"]' },
			hint: 'tour.gold.add.hint',
			advance: true,
			optional: true,
			...at
		},
		{
			id: 'modality',
			target: 'gold-modality',
			title: 'tour.gold.modality.title',
			body: 'tour.gold.modality.body',
			example: 'tour.gold.modality.example',
			wait: { kind: 'change' },
			hint: 'tour.gold.modality.hint',
			missing: 'tour.gold.modality.missing',
			...at
		},
		{
			id: 'select',
			target: 'gold-text',
			title: 'tour.gold.select.title',
			body: 'tour.gold.select.body',
			example: 'tour.gold.select.example',
			wait: { kind: 'selection', within: '[data-tour="gold-text"]' },
			hint: 'tour.gold.select.hint',
			padding: 10,
			missing: 'tour.gold.read.missing',
			...at
		},
		{
			id: 'fill',
			target: 'gold-norm',
			pick: 'last',
			title: 'tour.gold.fill.title',
			body: 'tour.gold.fill.body',
			wait: { kind: 'click', within: '[data-tour="gold-fill"]' },
			hint: 'tour.gold.fill.hint',
			missing: 'tour.gold.modality.missing',
			...at
		},
		{ id: 'several', target: 'gold-add-norm', title: 'tour.gold.several.title', body: 'tour.gold.several.body', example: 'tour.gold.several.example', optional: true, ...at },
		{ id: 'save', target: 'gold-save', title: 'tour.gold.save.title', body: 'tour.gold.save.body', placement: 'top', optional: true, ...at },
		{ id: 'exchange', target: 'tab-exchange', title: 'tour.gold.exchange.title', body: 'tour.gold.exchange.body', optional: true, ...at },
		{ id: 'done', title: 'tour.gold.done.title', body: 'tour.gold.done.body' }
	]
};
