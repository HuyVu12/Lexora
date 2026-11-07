import type { Account } from './types';

export const session = $state<{ account: Account | null; checked: boolean }>({ account: null, checked: false });

export function canReview(account: Account | null): boolean {
	return account?.role === 'admin' || account?.role === 'reviewer';
}
