"""English versions of the glossary entries in `glossary.py` (same keys).

Examples stay Vietnamese because the statute text is always Vietnamese; only the term, the
definition and the cue description are translated.
"""

GLOSSARY_EN = {
    "norm": {"term": "Norm", "definition": "A rule of conduct drawn from one sentence of the statute: who must, may or must not do what, and under which conditions. Lexora splits each norm into parts you check against the exact text."},
    "modality": {"term": "Modality", "definition": "Whether the sentence obliges, forbids, permits or grants a right. Lexora recognises it from cue words such as “phải”, “không được”, “có quyền”."},
    "obligation": {"term": "Obligation", "definition": "Something the subject is required to do. Not doing it is a breach.", "cues": "phải, có nghĩa vụ, có trách nhiệm, bắt buộc, buộc"},
    "prohibition": {"term": "Prohibition", "definition": "Something the subject must not do.", "cues": "không được, cấm, nghiêm cấm, bị cấm"},
    "entitlement": {"term": "Right", "definition": "Something the subject is entitled to or may demand; the other side must respect or meet it.", "cues": "có quyền, được quyền"},
    "permission": {"term": "Permission", "definition": "The subject may do it but is not required to.", "cues": "có thể, được"},
    "definition": {"term": "Definition", "definition": "A sentence that explains a term used in the statute. It does not require anyone to act.", "cues": "là, được hiểu là"},
    "procedure": {"term": "Procedure", "definition": "The steps, form or documents needed to carry out something."},
    "unknown_modality": {"term": "Modality unknown", "definition": "Lexora found no modality cue word in the sentence. Select the cue word in the text to set the modality."},
    "actor": {"term": "Subject", "definition": "The person or organisation the norm addresses: who must, may or must not act."},
    "action": {"term": "Action", "definition": "What the subject does, may do or must not do. Usually the main verb of the sentence."},
    "object": {"term": "Object", "definition": "The thing, document or content the action applies to."},
    "beneficiary": {"term": "Beneficiary", "definition": "The person who benefits when the subject carries out the norm."},
    "recipient": {"term": "Recipient", "definition": "The person who receives the information, document or property the subject hands over."},
    "counterparty": {"term": "Counterparty", "definition": "The other party in the relationship the subject takes part in, such as the other signatory of a contract."},
    "outcome": {"term": "Outcome", "definition": "The legal consequence that follows when the norm applies."},
    "conditions": {"term": "Condition", "definition": "The circumstance that must exist for the norm to apply.", "cues": "khi, nếu, trường hợp, trong thời gian"},
    "exceptions": {"term": "Exception", "definition": "A case in which the norm does not apply even though the other conditions are met.", "cues": "trừ trường hợp, trừ khi, không áp dụng"},
    "quantities": {"term": "Quantity", "definition": "A number, rate, minimum or maximum attached to the norm."},
    "deadlines": {"term": "Deadline", "definition": "A period or a point in time that must be respected."},
    "scope": {"term": "Parent context", "definition": "The lead-in sentence of the article or clause the sentence belongs to. It applies to every point below it."},
    "references": {"term": "Reference", "definition": "Where the sentence mentions another article, clause or document. Lexora links a reference only when it finds the exact target and never guesses."},
    "gap": {"term": "Sentence without a norm", "definition": "A sentence of the statute that no norm was drawn from yet. Before publishing, each one needs a norm or a “not a norm” decision, so nothing is skipped."},
    "entity": {"term": "Entity", "definition": "A person, organisation or concept a norm mentions, such as “người lao động”. Two mentions count as the same entity only when a reviewer confirms it."},
    "source_unit": {"term": "Source unit", "definition": "The article, clause or point of the source document that holds the sentence the norm was drawn from."},
    "evidence": {"term": "Evidence", "definition": "A verbatim quote with its exact character position in the source text. Every part of a norm must have evidence."},
    "approved": {"term": "Approved norm", "definition": "A norm a reviewer has checked against the exact text and accepted. Only approved norms are used to answer questions. The legal validity of the document is still not verified."},
    "ai": {"term": "AI suggested", "definition": "A norm an AI model proposed for a sentence the rules could not structure. Every value it returns is checked to appear verbatim in the sentence; you still review it like any other norm."},
    "manual": {"term": "Added by hand", "definition": "A norm the reviewer added by selecting text in the statute."},
    "cue": {"term": "Needs completing", "definition": "The sentence has a modality cue but the rules could not find its subject or action. Use Edit and select the missing parts."},
    "attention": {"term": "Needs attention", "definition": "The norm shows signs that need a careful read, such as a negation, an exception or a missing subject."},
    "revision": {"term": "Revision", "definition": "Each publish creates a new revision of the knowledge base. Old revisions are kept, and chats already started keep using the revision they started with."},
    "private": {"term": "Private base", "definition": "Its content is never sent off this machine, even when AI is enabled."},
    "public": {"term": "Public base", "definition": "Its content may be sent to an AI service when you choose to use AI for a turn."},
    "context": {"term": "Context", "definition": "The lead-in of the article or clause that holds the quote. Read it with the quote to understand where it applies."},
}
