import { redirect } from '@sveltejs/kit';

// The knowledge bases are listed on the overview; /kb on its own leads there instead of a dead end.
export const load = () => redirect(307, '/');
