import type { Tour } from '../types.js';

const page = /^\/chat(\/|$)/;
const at = { page, route: '/chat' };

/**
 * Asking on the reviewed bases: scope, a full question, the waiting stage, the answer and its sources.
 * The tour never sends a question: the user does, and the next steps wait for the answer to arrive.
 */
export const chatTour: Tour = {
	id: 'chat',
	version: 1,
	title: 'tour.chat.name',
	summary: 'tour.chat.summary',
	guides: [],
	start: '/chat',
	steps: [
		{ id: 'intro', title: 'tour.chat.intro.title', body: 'tour.chat.intro.body', ...at },
		{ id: 'new', target: 'chat-new', title: 'tour.chat.new.title', body: 'tour.chat.new.body', optional: true, ...at },
		{
			id: 'scope',
			target: 'chat-scope',
			title: 'tour.chat.scope.title',
			body: 'tour.chat.scope.body',
			wait: { kind: 'click' },
			hint: 'tour.chat.scope.hint',
			placement: 'top',
			...at
		},
		{
			id: 'ask',
			target: 'chat-composer',
			title: 'tour.chat.ask.title',
			body: 'tour.chat.ask.body',
			example: 'tour.chat.ask.example',
			demo: { kind: 'type' },
			fill: 'tour.chat.ask.fill',
			wait: { kind: 'input', min: 8 },
			hint: 'tour.chat.ask.hint',
			placement: 'top',
			missing: 'tour.chat.ask.missing',
			...at
		},
		{ id: 'mode', target: 'chat-options', title: 'tour.chat.mode.title', body: 'tour.chat.mode.body', placement: 'top', optional: true, ...at },
		{
			id: 'send',
			target: 'chat-send',
			title: 'tour.chat.send.title',
			body: 'tour.chat.send.body',
			wait: { kind: 'appear', selector: '[data-tour="chat-answer"] .body' },
			hint: 'tour.chat.send.hint',
			advance: true,
			placement: 'top',
			padding: 8,
			...at
		},
		{ id: 'answer', target: 'chat-answer', pick: 'last', title: 'tour.chat.answer.title', body: 'tour.chat.answer.body', missing: 'tour.chat.answer.missing', ...at },
		{
			id: 'cite',
			target: 'chat-cite',
			pick: 'last',
			title: 'tour.chat.cite.title',
			body: 'tour.chat.cite.body',
			wait: { kind: 'appear', selector: '[data-tour="chat-source"]' },
			hint: 'tour.chat.cite.hint',
			advance: true,
			missing: 'tour.chat.cite.missing',
			...at
		},
		{ id: 'source', target: 'chat-source', title: 'tour.chat.source.title', body: 'tour.chat.source.body', placement: 'left', optional: true, ...at },
		{ id: 'tools', target: 'chat-copy', pick: 'last', title: 'tour.chat.tools.title', body: 'tour.chat.tools.body', optional: true, ...at },
		{ id: 'none', title: 'tour.chat.none.title', body: 'tour.chat.none.body' },
		{ id: 'history', target: 'chat-history', title: 'tour.chat.history.title', body: 'tour.chat.history.body', optional: true, ...at },
		{ id: 'done', title: 'tour.chat.done.title', body: 'tour.chat.done.body' }
	]
};
