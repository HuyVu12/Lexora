import { loadAppState } from '#lib/app-state.svelte.js';
import type { Tour, TourContext } from '../types.js';

const page = /^\/drafts\/[^/]+$/;

/** The draft open now, or the first draft that is ready to review; null when there is none yet. */
async function draftRoute(ctx: TourContext): Promise<string | null> {
	if (page.test(ctx.path)) return ctx.path;
	const app = await loadAppState().catch(() => null);
	const draft = app?.drafts.find((d) => d.status === 'draft' && !['queued', 'running'].includes(d.extraction_state));
	return draft ? `/drafts/${draft.id}` : null;
}

const onDraft = { page, route: draftRoute };

/**
 * Reviewing a draft on the real data that is open: read the statute and the norm card, fix one part by
 * selecting its exact words, handle a sentence without a norm, then see where publishing happens.
 * The tour never approves, rejects, saves an edit or publishes: those buttons are only pointed at.
 */
export const reviewTour: Tour = {
	id: 'review',
	version: 1,
	title: 'tour.review.name',
	summary: 'tour.review.summary',
	roles: ['admin', 'reviewer'],
	guides: ['review'],
	steps: [
		{ id: 'intro', title: 'tour.review.intro.title', body: 'tour.review.intro.body', missing: 'tour.review.intro.missing', ...onDraft },
		{ id: 'progress', target: 'review-progress', title: 'tour.review.progress.title', body: 'tour.review.progress.body', ...onDraft },
		{
			id: 'text',
			target: 'review-text',
			prefer: ':has(.on)',
			title: 'tour.review.text.title',
			body: 'tour.review.text.body',
			demo: { kind: 'sweep', selector: '.hl.on, .hl' },
			...onDraft
		},
		{ id: 'key', target: 'review-key', title: 'tour.review.key.title', body: 'tour.review.key.body', optional: true, ...onDraft },
		{
			id: 'flag',
			target: 'review-flag',
			prefer: '[aria-pressed="true"]',
			title: 'tour.review.flag.title',
			body: 'tour.review.flag.body',
			wait: { kind: 'click', within: '[data-tour="review-flag"]' },
			hint: 'tour.review.flag.hint',
			missing: 'tour.review.flag.missing',
			padding: 8,
			...onDraft
		},
		{ id: 'card', target: 'norm-card', title: 'tour.review.card.title', body: 'tour.review.card.body', placement: 'left', ...onDraft },
		{
			id: 'decide',
			target: 'norm-decide',
			title: 'tour.review.decide.title',
			body: 'tour.review.decide.body',
			example: 'tour.review.decide.example',
			placement: 'left',
			...onDraft
		},
		{
			id: 'edit',
			target: 'norm-edit',
			title: 'tour.review.edit.title',
			body: 'tour.review.edit.body',
			wait: { kind: 'appear', selector: '[data-tour="norm-editor"]' },
			hint: 'tour.review.edit.hint',
			advance: true,
			placement: 'left',
			...onDraft
		},
		{
			id: 'field',
			target: 'norm-field',
			title: 'tour.review.field.title',
			body: 'tour.review.field.body',
			example: 'tour.review.field.example',
			wait: { kind: 'change' },
			hint: 'tour.review.field.hint',
			missing: 'tour.review.field.missing',
			placement: 'left',
			...onDraft
		},
		{
			id: 'select',
			target: 'review-text',
			prefer: ':has(.on)',
			title: 'tour.review.select.title',
			body: 'tour.review.select.body',
			example: 'tour.review.select.example',
			demo: { kind: 'sweep', selector: '.hl.on' },
			wait: { kind: 'selection', within: '.paper [data-uv]' },
			hint: 'tour.review.select.hint',
			padding: 10,
			...onDraft
		},
		{
			id: 'use',
			target: 'norm-use',
			title: 'tour.review.use.title',
			body: 'tour.review.use.body',
			missing: 'tour.review.use.missing',
			placement: 'left',
			...onDraft
		},
		{
			id: 'gap',
			target: 'review-gap',
			prefer: ':not(.done)',
			title: 'tour.review.gap.title',
			body: 'tour.review.gap.body',
			wait: { kind: 'click', within: '[data-tour="review-gap"]' },
			hint: 'tour.review.gap.hint',
			missing: 'tour.review.gap.missing',
			padding: 8,
			...onDraft
		},
		{ id: 'gapCard', target: 'gap-card', title: 'tour.review.gapCard.title', body: 'tour.review.gapCard.body', placement: 'left', optional: true, ...onDraft },
		{ id: 'batch', target: 'review-batch', title: 'tour.review.batch.title', body: 'tour.review.batch.body', optional: true, ...onDraft },
		{ id: 'preview', target: 'review-preview', title: 'tour.review.preview.title', body: 'tour.review.preview.body', placement: 'top', ...onDraft },
		{ id: 'done', title: 'tour.review.done.title', body: 'tour.review.done.body' }
	]
};
