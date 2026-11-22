import type { Tour } from '../types.js';
import { overview } from './overview.js';
import { importTour } from './import.js';
import { reviewTour } from './review.js';
import { chatTour } from './chat.js';
import { goldTour } from './gold.js';
import { questionsTour, compareTour } from './questions.js';
import { auditTour } from './audit.js';
import { corpusTour } from './corpus.js';
import { usersTour, monitorTour } from './admin.js';

/**
 * Every step-by-step tour, in the order the user menu lists them. To add one: write a step file next to
 * these (strings as one `tour.<id>.*` block in vi.ts and en.ts, targets as `data-tour` attributes on the
 * real elements), list it here, and name the PageGuide pages whose "?" should offer it in `guides`.
 */
export const TOURS: Tour[] = [overview, chatTour, importTour, reviewTour, goldTour, questionsTour, compareTour, auditTour, corpusTour, usersTour, monitorTour];
