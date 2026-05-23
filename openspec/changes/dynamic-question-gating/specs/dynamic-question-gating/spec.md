## ADDED Requirements

### Requirement: Deterministic Inquisitive Parsing
The system SHALL monitor the generated token stream and programmatically analyze completed spoken sentences for an interrogation marker (`?`).

#### Scenario: Sentence Ends With Question Mark
- **WHEN** a generated sentence terminates with a question mark (`?`)
- **THEN** the system SHALL forcefully assign `config.WAITING_FOR_CLARIFICATION = True` even if the model omitted the explicit `[CLARIFY]` tag.

### Requirement: Keyword Fallback Matching
The system SHALL scan generated sentence terminations for common conversational inquisitive check-backs.

#### Scenario: Suffix Matches Inquisitive Keyword
- **WHEN** a generated sentence ends with `"right?"`, `"agree?"`, `"you think?"`, or `"your take?"`
- **THEN** the system SHALL forcefully assign `config.WAITING_FOR_CLARIFICATION = True` and print a `[SYSTEM-FIX]` validation log.

### Requirement: Database Logging Sanitization
The system SHALL purge any raw `[CLARIFY]` tags and fallback markers from the logged conversation before serializing the turn into the SQLite database.

#### Scenario: Bot Turn Saved to Database
- **WHEN** a bot response contains `[CLARIFY]` or triggers fallback question gating
- **THEN** the system SHALL log the turn to SQLite with the `[CLARIFY]` tag completely removed.
