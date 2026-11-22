import type { Tour } from '../types.js';

const page = /^\/import$/;
const route = '/import';

/** From a law text to a draft: source, articles, where to store it, private or public, rules or AI. */
export const importTour: Tour = {
	id: 'import',
	version: 1,
	title: 'tour.import.name',
	summary: 'tour.import.summary',
	area: 'kb',
	roles: ['admin', 'reviewer'],
	guides: ['import'],
	start: route,
	next: 'review',
	steps: [
		{ id: 'intro', title: 'tour.import.intro.title', body: 'tour.import.intro.body', page, route },
		{
			id: 'source',
			target: 'import-source',
			title: 'tour.import.source.title',
			body: 'tour.import.source.body',
			page,
			route,
			wait: { kind: 'click', within: '[data-tour="import-source"] .choice' },
			hint: 'tour.import.source.hint'
		},
		{
			id: 'catalog',
			target: 'import-catalog',
			title: 'tour.import.catalog.title',
			body: 'tour.import.catalog.body',
			example: 'tour.import.catalog.example',
			demo: { kind: 'type' },
			page,
			route,
			optional: true,
			wait: { kind: 'input', min: 3 },
			hint: 'tour.import.catalog.hint'
		},
		{ id: 'articles', target: 'import-articles', title: 'tour.import.articles.title', body: 'tour.import.articles.body', page, route, optional: true },
		{
			id: 'docTitle',
			target: 'import-doc-title',
			title: 'tour.import.docTitle.title',
			body: 'tour.import.docTitle.body',
			example: 'tour.import.docTitle.example',
			fill: 'tour.import.docTitle.fill',
			page,
			route,
			optional: true,
			wait: { kind: 'input', min: 3 },
			hint: 'tour.import.docTitle.hint'
		},
		{
			id: 'paste',
			target: 'import-paste',
			title: 'tour.import.paste.title',
			body: 'tour.import.paste.body',
			example: 'tour.import.paste.example',
			page,
			route,
			optional: true
		},
		{ id: 'target', target: 'import-target', title: 'tour.import.target.title', body: 'tour.import.target.body', page, route },
		{
			id: 'kbName',
			target: 'import-kb-name',
			title: 'tour.import.kbName.title',
			body: 'tour.import.kbName.body',
			example: 'tour.import.kbName.example',
			fill: 'tour.import.kbName.fill',
			demo: { kind: 'type' },
			page,
			route,
			missing: 'tour.import.kbName.missing',
			wait: { kind: 'input', min: 3 },
			hint: 'tour.import.kbName.hint'
		},
		{ id: 'dataClass', target: 'import-dataclass', title: 'tour.import.dataClass.title', body: 'tour.import.dataClass.body', page, route, optional: true },
		{ id: 'method', target: 'import-method', title: 'tour.import.method.title', body: 'tour.import.method.body', page, route },
		{ id: 'submit', target: 'import-submit', title: 'tour.import.submit.title', body: 'tour.import.submit.body', page, route, placement: 'top' },
		{ id: 'done', title: 'tour.import.done.title', body: 'tour.import.done.body' }
	]
};
