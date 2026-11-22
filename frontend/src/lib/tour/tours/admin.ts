import type { Tour } from '../types.js';

const users = { page: /^\/admin\/users$/, route: '/admin/users' };

/** Account management for admins. Every action is explained, never pressed. */
export const usersTour: Tour = {
	id: 'users',
	version: 1,
	title: 'tour.users.name',
	summary: 'tour.users.summary',
	roles: ['admin'],
	guides: ['users'],
	steps: [
		{ id: 'create', target: 'users-create', title: 'tour.users.create.title', body: 'tour.users.create.body', ...users },
		{ id: 'roles', target: 'users-roles', title: 'tour.users.roles.title', body: 'tour.users.roles.body', ...users },
		{ id: 'list', target: 'users-list', title: 'tour.users.list.title', body: 'tour.users.list.body', ...users },
		{ id: 'done', title: 'tour.users.done.title', body: 'tour.users.done.body' }
	]
};

const dev = { page: /^\/dev$/, route: '/dev' };

/** The monitoring pages for admin and dev: tabs, alerts, limits and switches, the report export. */
export const monitorTour: Tour = {
	id: 'monitor',
	version: 1,
	title: 'tour.monitor.name',
	summary: 'tour.monitor.summary',
	roles: ['admin', 'dev'],
	guides: ['dev'],
	steps: [
		{ id: 'tabs', target: 'tabs', title: 'tour.monitor.tabs.title', body: 'tour.monitor.tabs.body', ...dev },
		{ id: 'alerts', target: 'dev-alerts', title: 'tour.monitor.alerts.title', body: 'tour.monitor.alerts.body', optional: true, ...dev },
		{ id: 'controls', target: 'dev-controls', title: 'tour.monitor.controls.title', body: 'tour.monitor.controls.body', optional: true, ...dev },
		{ id: 'report', target: 'tab-report', title: 'tour.monitor.report.title', body: 'tour.monitor.report.body', optional: true, ...dev },
		{ id: 'done', title: 'tour.monitor.done.title', body: 'tour.monitor.done.body' }
	]
};
