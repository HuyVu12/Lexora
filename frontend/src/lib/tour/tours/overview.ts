import type { Tour } from '../types.js';

const REVIEW = ['admin', 'reviewer'] as const;

/** First orientation for every role: the main areas, where things live, language, account menu and the "?". */
export const overview: Tour = {
	id: 'overview',
	version: 1,
	title: 'tour.overview.name',
	summary: 'tour.overview.summary',
	guides: ['homeReviewer', 'homeReader'],
	start: '/',
	next: 'import',
	steps: [
		{ id: 'welcome', title: 'tour.overview.welcome.title', body: 'tour.overview.welcome.body', page: /^\/$/, route: '/' },
		{ id: 'home', target: 'nav-home', title: 'tour.overview.home.title', body: 'tour.overview.home.body', page: /^\/$/, route: '/' },
		{
			id: 'drafts',
			target: 'home-drafts',
			roles: [...REVIEW],
			title: 'tour.overview.drafts.title',
			body: 'tour.overview.drafts.body',
			page: /^\/$/,
			route: '/',
			optional: true
		},
		{ id: 'kbs', target: 'home-kbs', title: 'tour.overview.kbs.title', body: 'tour.overview.kbs.body', page: /^\/$/, route: '/', optional: true },
		{ id: 'chats', target: 'home-chats', title: 'tour.overview.chats.title', body: 'tour.overview.chats.body', page: /^\/$/, route: '/', optional: true },
		{ id: 'chat', target: 'nav-chat', title: 'tour.overview.chat.title', body: 'tour.overview.chat.body', example: 'tour.overview.chat.example', optional: true },
		{ id: 'import', target: 'nav-import', roles: [...REVIEW], title: 'tour.overview.import.title', body: 'tour.overview.import.body', optional: true },
		{ id: 'research', target: 'nav-research', roles: [...REVIEW], title: 'tour.overview.research.title', body: 'tour.overview.research.body', optional: true },
		{ id: 'monitor', target: 'nav-monitor', roles: ['dev'], title: 'tour.overview.monitor.title', body: 'tour.overview.monitor.body', optional: true },
		{ id: 'docs', target: 'nav-docs', title: 'tour.overview.docs.title', body: 'tour.overview.docs.body', optional: true },
		{ id: 'lang', target: 'lang-switch', title: 'tour.overview.lang.title', body: 'tour.overview.lang.body' },
		{
			id: 'account',
			target: 'user-menu',
			title: 'tour.overview.account.title',
			body: 'tour.overview.account.body',
			wait: { kind: 'click' },
			hint: 'tour.overview.account.hint'
		},
		{
			id: 'guide',
			target: 'guide-button',
			title: 'tour.overview.guide.title',
			body: 'tour.overview.guide.body',
			page: /^\/$/,
			route: '/',
			padding: 8
		},
		{ id: 'done', title: 'tour.overview.done.title', body: 'tour.overview.done.body' }
	]
};
