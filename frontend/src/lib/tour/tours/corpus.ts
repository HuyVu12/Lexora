import type { Tour, TourContext } from '../types.js';
import { firstOf } from './routes.js';

const list = /^\/research$/;
const corpus = /^\/research\/(?!questions$|gold$|audit$|results$)[^/]+$/;
const doc = /^\/research\/[^/]+\/document\/[^/]+$/;

const onList = { page: list, route: '/research' };
const onCorpus = { page: corpus, route: firstOf(corpus, '/api/corpora', 'corpora', (id) => `/research/${id}`) };

/** A document of the open corpus (the first one listed), or the document already open. */
function documentRoute(ctx: TourContext): string | null {
	if (doc.test(ctx.path)) return ctx.path;
	return document.querySelector('[data-tour="corpus-docs"] a[href*="/document/"]')?.getAttribute('href') ?? null;
}

/** Back from a document to its corpus. */
function corpusRoute(ctx: TourContext): string | null {
	if (corpus.test(ctx.path)) return ctx.path;
	const match = ctx.path.match(/^(\/research\/[^/]+)\/document\//);
	return match ? match[1] : null;
}

/**
 * Research corpora, following docs/features/question-annotation.md: create one, add documents, check the
 * parser warnings of a document, freeze a version. Creating, fetching and freezing are explained, never pressed.
 */
export const corpusTour: Tour = {
	id: 'corpus',
	version: 1,
	title: 'tour.corpus.name',
	summary: 'tour.corpus.summary',
	area: 'research',
	roles: ['admin', 'reviewer'],
	guides: ['corpora', 'corpus', 'document'],
	steps: [
		{ id: 'intro', title: 'tour.corpus.intro.title', body: 'tour.corpus.intro.body', ...onList },
		{ id: 'create', target: 'corpus-create', title: 'tour.corpus.create.title', body: 'tour.corpus.create.body', ...onList },
		{ id: 'list', target: 'corpus-list', title: 'tour.corpus.list.title', body: 'tour.corpus.list.body', ...onList },
		{ id: 'add', target: 'corpus-add', title: 'tour.corpus.add.title', body: 'tour.corpus.add.body', missing: 'tour.corpus.add.missing', ...onCorpus },
		{ id: 'docs', target: 'corpus-docs', title: 'tour.corpus.docs.title', body: 'tour.corpus.docs.body', ...onCorpus },
		{ id: 'parser', target: 'doc-warnings', title: 'tour.corpus.parser.title', body: 'tour.corpus.parser.body', missing: 'tour.corpus.parser.missing', page: doc, route: documentRoute },
		{ id: 'freeze', target: 'corpus-versions', title: 'tour.corpus.freeze.title', body: 'tour.corpus.freeze.body', page: corpus, route: corpusRoute },
		{ id: 'done', title: 'tour.corpus.done.title', body: 'tour.corpus.done.body' }
	]
};
