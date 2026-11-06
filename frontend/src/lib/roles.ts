import type { MessageKey } from './i18n/vi';

/** Order in which a norm's parts are listed on its card. */
export const SLOT_ORDER = [
	'actor', 'action', 'object', 'beneficiary', 'recipient', 'counterparty',
	'conditions', 'exceptions', 'quantities', 'deadlines', 'outcome'
] as const;

/** Highlighter colour for each part. Related parties and conditions share a pen so the page keeps five colours. */
export const ROLE_CLASS: Record<string, string> = {
	actor: 'hl-actor',
	action: 'hl-action',
	object: 'hl-object',
	beneficiary: 'hl-party',
	recipient: 'hl-party',
	counterparty: 'hl-party',
	conditions: 'hl-condition',
	exceptions: 'hl-condition',
	quantities: 'hl-measure',
	deadlines: 'hl-measure',
	outcome: 'hl-other'
};

export const KEY_GROUPS: { cls: string; slots: string[] }[] = [
	{ cls: 'hl-actor', slots: ['actor'] },
	{ cls: 'hl-action', slots: ['action'] },
	{ cls: 'hl-object', slots: ['object'] },
	{ cls: 'hl-party', slots: ['recipient', 'beneficiary', 'counterparty'] },
	{ cls: 'hl-condition', slots: ['conditions', 'exceptions'] },
	{ cls: 'hl-measure', slots: ['quantities', 'deadlines'] }
];

export const MODALITIES = ['obligation', 'prohibition', 'entitlement', 'permission', 'definition', 'procedure'] as const;

export const slotKey = (slot: string) => `slot.${slot}` as MessageKey;
export const modalityKey = (modality: string) => `modality.${modality}` as MessageKey;
/** Glossary key for a modality (the glossary names the unknown one differently). */
export const modalityTerm = (modality: string) => (modality === 'unknown' ? 'unknown_modality' : modality);
