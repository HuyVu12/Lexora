import type { Account } from './types';

export const session = $state<{ account: Account | null; checked: boolean }>({ account: null, checked: false });

export function canReview(account: Account | null): boolean {
	return account?.role === 'admin' || account?.role === 'reviewer';
}

/** Admin and dev see the monitoring pages; only dev changes limits, switches and report notes. */
export function canMonitor(account: Account | null): boolean {
	return account?.role === 'admin' || account?.role === 'dev';
}

/** Reviewers, admins and devs see the research results page. */
export function canSeeResults(account: Account | null): boolean {
	return canReview(account) || account?.role === 'dev';
}
