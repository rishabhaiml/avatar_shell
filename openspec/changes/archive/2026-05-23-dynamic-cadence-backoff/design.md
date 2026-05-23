## Context

In B.H.A.I.'s proactive follow-up modes, turn taking snappiness (600ms trailing quiet threshold) is highly desirable to prevent awkward pauses. However, when users are interrupted mid-thought because they pause briefly to frame their next clause (especially after conjunctions like "because" or "and"), the strict cut-off breaks the illusion of standard human dialogue. Since raw PCM frame energy matrices do not contain linguistic semantic data, a fast-pass, parallel partial Whisper STT check is required.

## Goals / Non-Goals

**Goals:**
- Dynamically double the quiet threshold (to 1200ms) only when users pause on conjunctions, keeping standard turns at 600ms for snappiness.
- Maintain a non-blocking real-time capture loop thread (never block GTK or pyaudio capture callbacks).

**Non-Goals:**
- Modifying Whisper model sizes or parameters during active check tasks.
- Modifying standard `AppState.LISTENING` wake turn silence thresholds.

## Decisions

### Decision 1: Parallel Threaded Partial Suffix Sniffer
**Choice**: Spawn a daemon background `threading.Thread` with a copy of `config.command_audio_buffer` the instant `consecutive_quiet` hits 1.
- **Why**: Whisper model inference has standard CPU latency (~50-150ms for small segments on base models). Spawning a background thread prevents blocking the primary GTK state timer or audio pipeline loops.
- **Alternatives Considered**: 
  - *Inline evaluation*: Discarded because it blocks the state machine loop, causing immediate audio frame drops and GTK UI stuttering.
  - *Full asynchronous worker queues*: Overkill for a simple micro-pass check.

### Decision 2: Greedy Search Suffix Matching
**Choice**: Run transcription using `beam_size=1` (greedy search) on the trailing audio snapshot, extract the final word, and match against a set list of loose conjunctions (`"because"`, `"but"`, `"so"`, `"and"`, `"or"`, `"if"`, `"then"`, `"like"`).
- **Why**: Greedy search is computationally lightweight and runs in a fraction of standard beam-search time, giving instant results within ~50ms to scale the threshold dynamically before the 600ms barrier is reached.

## Risks / Trade-offs

- **[Risk]** Background Whisper inference competes for CPU threads with active speech synthesis or window graphics.
  - *Mitigation*: Run background checks strictly with `beam_size=1` and only when `CADENCE_CHECK_IN_PROGRESS = False` to prevent spawning concurrent overlapping checking threads on sustained quietness.
