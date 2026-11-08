export type Role = 'admin' | 'reviewer' | 'reader' | 'dev';

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
	extraction_via?: 'claude' | '9router' | null;
	extraction_calls_left?: number;
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

export interface EffectStatus {
	code: string | null;
	name: string | null;
}

export interface CorpusDocument {
	id: string;
	document_id: string;
	title: string;
	source_kind: 'vbpl' | 'file';
	source_ref: string;
	source_url: string;
	source_sha256: string;
	accessed_at: string;
	metadata: { effect_status?: EffectStatus | null; doc_num?: string; format?: string; filename?: string; effective_from?: string | null };
	added_at: string;
	added_by: string;
	unit_count: number;
	article_count: number;
	leaf_count: number;
	audit_count: number;
	unassigned_characters: number;
	trailing_characters: number;
	parser_version: string;
	warnings: string[];
}

export interface CorpusVersion {
	id: string;
	number: number;
	note: string;
	frozen_at: string;
	frozen_by: string;
	document_rows: string[];
	bundle_sha256: string;
	document_count: number;
	unit_count: number;
}

export interface CorpusSummary {
	id: string;
	name: string;
	description: string;
	created_at: string;
	created_by: string;
	documents: number;
	latest_version: number | null;
}

export interface CorpusDetail extends Omit<CorpusSummary, 'documents' | 'latest_version'> {
	documents: CorpusDocument[];
	versions: CorpusVersion[];
	changed_since_version: boolean;
}

export interface CorpusListing {
	corpora: CorpusSummary[];
	vbpl_enabled: boolean;
	catalog: { documents: number; revisions: Record<string, string>; built_at: string } | null;
}

export interface CatalogEntry {
	vbpl_id: string;
	doc_num: string | null;
	title: string;
	doc_type: string | null;
	issue_date: string | null;
	effect_status: string | null;
	agency: string | null;
	in_force: boolean;
	usually_no_articles: boolean;
	sources: string[];
}

export interface ParsedUnit {
	unit_id: string;
	unit_type: 'chapter' | 'section' | 'article' | 'clause' | 'point';
	parent_id: string | null;
	label: string;
	text: string;
	source_start: number;
}

export interface CorpusDocumentDetail extends CorpusDocument {
	corpus_id: string;
	removed_at: string | null;
	units: ParsedUnit[];
	audit: { code: string; offset: number; unit_id?: string }[];
	unassigned_text: string;
	trailing_text: string;
}

export type QuestionType = 'lookup' | 'synthesis' | 'temporal' | 'out_of_scope';
export type ExpectedStatus = 'answer' | 'refuse';

export interface LabelFields {
	question_type: QuestionType | null;
	expected_status: ExpectedStatus | null;
	relevant_unit_ids: string[];
}

export interface QuestionProposal {
	id: string;
	fields: LabelFields;
	rationale: string;
	candidates: string[];
	created_at: string;
}

export interface QuestionItem {
	id: string;
	position: number;
	text: string;
	family_id: string;
	origin: 'human' | 'model';
	origin_detail: { edited?: boolean; call_id?: string; imported?: boolean };
	created_by: string;
	label: { fields: LabelFields; note: string; provenance: { proposals_shown: boolean; decisions: Record<string, string> }; updated_at: string } | null;
	proposal: QuestionProposal | null;
}

export interface QuestionSetSummary {
	id: string;
	name: string;
	corpus_version_id: string;
	corpus_id: string;
	corpus_version: number;
	guideline: string;
	created_by: string;
	created_at: string;
	imported: boolean;
	frozen: FrozenQuestions | null;
	questions: number | null;
}

export interface FrozenQuestions {
	frozen_at: string;
	frozen_by: string;
	seed: string;
	held_out_fraction: number;
	bundle_sha256: string;
	counts: Record<string, number>;
	agreement: Record<string, number | null>;
	questions_sha256: string;
}

export interface QuestionWorkspace extends QuestionSetSummary {
	show_proposals: boolean | null;
	items: QuestionItem[];
	labelled: number;
	annotators: { annotator: string; annotator_name: string; imported: number; labels: number }[];
	calls: number;
	proposal_model: string | null;
	proposal_calls_left: number;
}

export interface FrozenVersionOption {
	id: string;
	corpus_id: string;
	corpus_name: string;
	number: number;
	document_count: number;
	unit_count: number;
	frozen_at: string;
}

export interface UnitCandidate {
	unit_id: string;
	path: string;
	text: string;
}

export interface QuestionDraft {
	id: string;
	unit_ids: string[];
	drafts: { text: string; question_type: QuestionType; relevant_unit_ids: string[]; paraphrases: string[]; rationale: string }[];
	accepted: number[];
}

export interface ComparedItem extends QuestionItem {
	first: (LabelFields & { note: string }) | null;
	second: (LabelFields & { note: string }) | null;
	agree: boolean;
	final: (LabelFields & { note: string; decided_by: string }) | null;
}

export interface Comparison {
	first: { annotator: string; name: string | null; proposals_shown: boolean | null };
	second: { annotator: string; name: string | null; proposals_shown: boolean | null };
	questions: number;
	labelled_by_both: number;
	kappa_question_type: number | null;
	kappa_expected_status: number | null;
	mean_unit_dice: number | null;
	exact_unit_match: number | null;
	full_agreement: number | null;
	adjudicated: number;
	items: ComparedItem[];
}

export interface OutlineArticle {
	id: string;
	heading: string;
	chapter: string | null;
	section: string | null;
	blocked: boolean;
	reason: string | null;
}

export interface VbplImport {
	vbpl_id: string;
	source_sha256: string;
	site_url: string;
	accessed_at: string;
	metadata: { title?: string; doc_num?: string; doc_type?: string; effect_status?: EffectStatus | null; issue_date?: string | null };
	articles: OutlineArticle[];
}

export type GoldModality = 'obligation' | 'prohibition' | 'entitlement' | 'permission' | 'unknown';

export interface GoldNorm {
	modality: GoldModality;
	modality_cue: string | null;
	slots: Partial<Record<string, string>>;
}

export interface GoldSetSummary {
	id: string;
	name: string;
	corpus_version_id: string;
	corpus_version: number;
	articles: number;
	sentences: number;
	created_by: string;
	created_at: string;
	imported: boolean;
	labelled: Record<string, number>;
	adjudicated: number;
}

export interface GoldItem {
	key: string;
	unit_id: string;
	text: string;
	path: string;
	document_title: string;
	context: string | null;
	norms: GoldNorm[] | null;
}

export interface GoldWorkspace extends GoldSetSummary {
	items: GoldItem[];
	annotator: string;
	slots: string[];
	modalities: GoldModality[];
	annotators: { annotator: string; annotator_name: string; imported: number; labels: number }[];
}

export interface GoldAgreement {
	sentences: number;
	kappa_has_norm: number | null;
	kappa_modality_matched: number | null;
	matched_norm_pairs: number;
	f1_strict: { norms: number | null; slots: number | null };
	f1_lenient: { norms: number | null; slots: number | null };
}

export interface GoldComparison {
	first: string;
	second: string;
	sentences: number;
	labelled_by_both: number;
	agreement: GoldAgreement | null;
	adjudicated: number;
	items: { key: string; unit_id: string; text: string; first: GoldNorm[] | null; second: GoldNorm[] | null; agree: boolean; final: { norms: GoldNorm[]; decided_by: string } | null }[];
}

export interface KbInjection {
	run: string;
	validator_version: string;
	clean_claims: number;
	false_reject_rate: number | null;
	detectable_rate: number | null;
	semantic_rate: number | null;
	by_type: Record<string, { injected: number; detection_rate: number | null; expected_detectable: boolean }>;
}

export interface KbRunSummary {
	run: string;
	run_id: string;
	created_at: string;
	provider: string;
	model: string;
	effort: string | null;
	max_tokens: number | null;
	validator_version: string | null;
	batches_planned: number | null;
	batches_attempted: number;
	batches_ok: number;
	batch_errors: Record<string, number>;
	calls_made: number;
	sentences_attempted: number;
	sentences_without_answer: number | null;
	dk3_claims: number;
	dk4_claims: number;
	rejected: number;
	rejected_rate: number | null;
	reasons: Record<string, number>;
	modality_unverified_rate: number | null;
	prompt_tokens: number;
	completion_tokens: number;
	reasoning_tokens: number;
	call_errors: Record<string, number>;
	call_error_rate: number | null;
	sentence_answer_rate: number | null;
	claims_per_sentence: number | null;
	completion_tokens_per_claim: number | null;
	median_call_seconds: number | null;
	calling_minutes: number | null;
	cost_usd: number | null;
	injection: KbInjection | null;
	report_stale: boolean;
	rejection_explained: { categories: Record<string, number>; values_found: Record<string, number> } | null;
}

// Monitoring (/api/dev/*): metadata and counts only, never prompts, answers or questions.
export type Feature = 'chat' | 'extraction' | 'proposal' | 'embedding';
export interface FeatureControl {
	enabled: boolean;
	daily_limit: number | null;
}
export interface ModelInUse {
	model: string;
	provider: string;
	calls: number | null;
	max_calls: number | null;
}
export interface DevAlert {
	level: 'critical' | 'warning';
	code: 'error_rate' | 'disabled' | 'near_limit' | 'run_budget' | 'blocked';
	feature?: Feature;
	value?: number;
	used?: number;
	limit?: number;
}
export interface DevToday {
	calls: number;
	errors: number;
	blocked: number;
	prompt_tokens: number;
	completion_tokens: number;
	cost_usd: number;
	by_feature: Record<Feature, number>;
}
export interface DevChange {
	at: string;
	actor: string;
	key: string;
	before: string | null;
	after: string;
}
export interface DevOverview {
	today: DevToday;
	controls: Record<Feature, FeatureControl>;
	models: Record<Feature, ModelInUse | null>;
	alerts: DevAlert[];
	can_change: boolean;
	running: { id: string; title: string; kb_name: string }[];
	changes: DevChange[];
	started_at: string;
}
export interface DevCallModel {
	feature: Feature;
	provider: string;
	model: string;
	calls: number;
	errors: number;
	requests: number;
	prompt_tokens: number;
	completion_tokens: number;
	reasoning_tokens: number;
	cost_usd: number;
	error_rate: number;
	p50_ms: number | null;
	p95_ms: number | null;
}
export interface DevCallRow {
	at: string;
	feature: Feature;
	purpose: string | null;
	provider: string;
	model: string;
	actor: string | null;
	status: 'ok' | 'error' | 'blocked';
	code: string | null;
	prompt_tokens: number;
	completion_tokens: number;
	cost_usd: number | null;
	duration_ms: number | null;
}
export interface DevCalls {
	days: number;
	daily: { day: string; features: Record<Feature, { ok: number; error: number; blocked: number }> }[];
	models: DevCallModel[];
	codes: Record<string, number>;
	recent: DevCallRow[];
}
export interface DevUsage {
	days: number;
	daily: { day: string; login_ok: number; login_refused: number; login_locked: number; questions: number }[];
	questions: number;
	by_mode: { extractive: number; llm: number };
	semantic: number;
	status: Record<string, number>;
	no_evidence_rate: number | null;
	citations_mean: number | null;
	p50_ms: number | null;
	p95_ms: number | null;
	accounts: Record<string, number>;
	active_sessions: number;
}
export interface DevKb {
	knowledge_bases: { id: string; name: string; data_class: string; revisions: number; documents: number; approved_claims: number; updated_at: string; archived_at: string | null }[];
	drafts: { id: string; title: string; kb_name: string; status: string; extraction_state: string; claims: number; decided: number; created_at: string }[];
	publishes_by_reviewer: Record<string, number>;
	corpora: { id: string; name: string; documents: number; latest_version: number | null }[];
	question_sets: { id: string; name: string; questions: number; frozen: unknown; created_at: string }[];
	gold_sets: { id: string; name: string; sentences: number; labelled: Record<string, number>; adjudicated: number; created_at: string }[];
}
export interface DevSystem {
	started_at: string;
	python: string;
	platform: string;
	commit: string | null;
	store: { path: string; bytes: number | null };
	frontend_built_at: string | null;
	models: Record<Feature, ModelInUse | null>;
	vbpl_enabled: boolean;
	catalog: unknown;
	experiments_dir: string;
	source_catalog: boolean;
}
export interface DevRun {
	name: string;
	kind: 'kb' | 'retrieval' | 'answer' | 'injection' | 'other';
	created_at: string | null;
}
export interface DevAudit {
	name: string;
	items: number;
	sheets: { file: string; items: number; labelled: number }[];
}
export interface DevExperiments {
	runs: DevRun[];
	kb: KbRunSummary[];
	audits: DevAudit[];
	validator_version: string;
}
export type NoteKey = 'limitations' | 'next_steps' | 'questions';
export interface ReportRow {
	model: string;
	provider: string;
	batches_ok: number;
	batches_planned: number | null;
	sentence_answer_rate: number | null;
	dk3: number;
	dk4: number;
	rejected: number;
	rejected_rate: number | null;
	detectable_rate: number | null;
	semantic_rate: number | null;
	call_error_rate: number | null;
	explained: Record<string, number>;
}
export interface DevReport {
	report_version: string;
	generated_at: string;
	status: { rq: string; title: string; facts: string; state: 'done' | 'partial' | 'todo' }[];
	extraction: ReportRow[];
	sampled_models: string[];
	audits: DevAudit[];
	notes: Record<NoteKey, string[]>;
	can_change: boolean;
}
