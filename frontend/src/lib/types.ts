export type Role = 'admin' | 'reviewer' | 'reader';

export interface Account {
	id: number;
	username: string;
	display_name: string;
	role: Role;
	active: boolean;
	created_at: string;
}

export interface KbSummary {
	id: string;
	name: string;
	description: string;
	data_class: 'private' | 'public';
	created_at: string;
	updated_at: string;
	current_revision: string;
	approved_claims: number;
	documents: number;
	revisions: number;
}

export interface DraftTarget {
	mode: 'new' | 'merge';
	name?: string;
	kb_id?: string;
	data_class?: string;
	description?: string;
}

export interface DraftSummary {
	id: string;
	title: string;
	status: string;
	created_at: string;
	target: DraftTarget;
	kb_name: string;
	extraction_state: string;
	claims: number;
	decided: number;
}

export interface ChatSessionSummary {
	id: string;
	created_at: string;
	turns: number;
	bindings: { kb_id: string; kb_name: string | null; revision: string }[];
}

export interface AppState {
	knowledge_bases: KbSummary[];
	drafts: DraftSummary[];
	chat_sessions: ChatSessionSummary[];
	account: Account;
	router_enabled: boolean;
	extraction_model: string | null;
	embedding_model: string | null;
}

export interface Evidence {
	unit_id: string;
	unit_version_id: string;
	start: number;
	end: number;
	quote: string;
	normalized_sha256: string;
	evidence_id?: string;
}

export interface Slot {
	state: 'present' | 'not_present' | 'unknown';
	text?: string;
	evidence?: Evidence[];
}

export interface Claim {
	id: string;
	label: string;
	unit_id: string;
	article_id: string;
	origin: string;
	ai_note: string | null;
	modality: string;
	modality_evidence: Evidence[];
	quote: Evidence | null;
	slots: Record<string, Slot>;
	decision: 'approve' | 'reject' | null;
	decision_mode?: string;
	reasons: string[];
	edited: boolean;
	edits: unknown[];
	reviewer_note?: string;
}

export interface Unit {
	unit_id: string;
	unit_version_id: string;
	unit_type: string;
	label: string;
	text: string;
}

export interface Article {
	id: string;
	label: string;
	units: Unit[];
}

export interface Gap {
	id: string;
	article_id: string;
	unit_version_id: string;
	start: number;
	end: number;
	text: string;
	decision: string | null;
	ai_note?: string | null;
}

export interface Progress {
	total: number;
	approved: number;
	rejected: number;
	edited: number;
	undecided: number;
	gaps: number;
	gaps_open: number;
}

export interface EntityLink {
	id: string;
	claim_id: string;
	label: string;
	context?: string;
	target?: string;
	decision: string | null;
	suggestions: { id: string; label: string; context?: string }[];
}

export interface Draft {
	id: string;
	title: string;
	status: string;
	target: DraftTarget;
	kb: { id: string; name: string } | null;
	document: { synthetic: boolean; source_url?: string };
	articles: Article[];
	claims: Claim[];
	gaps: Gap[];
	progress: Progress;
	entities: EntityLink[];
	unassigned_text: string;
	extraction: { mode: string; state: string; model: string; done: number; total: number; checked: number; ai_claims: number; errors: string[] };
	diff: {
		approved: number;
		rejected: number;
		edited: number;
		documents_before: number;
		documents_after: number;
		claims_before: number;
		claims_after: number;
		entities_linked: number;
		entities_new: number;
		warnings: string[];
	};
}

export interface KbDetail {
	id: string;
	name: string;
	description: string;
	data_class: 'private' | 'public';
	current_revision: string;
	approved_claims: number;
	documents: { title: string; source_url: string; synthetic: boolean }[];
	revisions: { id: string; created_at: string; reviewer: string | null; reason: string }[];
}

export interface Citation {
	id: string;
	title: string;
	evidence: Evidence;
	scope: { quote: string }[];
	sources: { kb_name: string; revision: string }[];
	edited: boolean;
	synthetic: boolean;
	source_url: string;
	similarity?: number | null;
	dense_rank?: number | null;
	lexical_rank?: number | null;
}

export interface Turn {
	question: string;
	mode?: string;
	retrieval?: { mode: string };
	status: string;
	error_code?: string | null;
	statements: { text: string; citation_ids: string[] }[];
	citations: Citation[];
	note: string;
}

export interface ChatSession {
	id: string;
	bindings: { kb_id: string; kb_name: string; revision: string }[];
	turns: Turn[];
}

export interface SourceEntry {
	id: string;
	title: string;
	downloaded_at: string;
}
