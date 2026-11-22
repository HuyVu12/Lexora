import { redirect } from '@sveltejs/kit';

// Drafts in review are listed on the overview; /drafts on its own leads there instead of a dead end.
export const load = () => redirect(307, '/');
