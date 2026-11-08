# Humark Confirmed Behavioral Defect Log

This document records confirmed behavioral defects discovered during working-run verification or user testing.

## B-001 — Physical Number Key Input Failure on Challenge Card
- **Observed Behavior**: User reported key '1' does not register selection for Option A while 'A' worked.
- **Design Vulnerability**: Coupling keyboard shortcuts solely to `KeyboardEvent.key` rather than checking hardware-agnostic `KeyboardEvent.code` (`Digit1`, `Numpad1`).
- **Structural Resolution**: Check both character value (`e.key`) and physical key code (`e.code`) for top-row numbers, numpad numbers, and character letters (`Digit1`/`Digit2`, `Numpad1`/`Numpad2`, `KeyA`/`KeyB`).
- **Design Heuristic**: For gaming and speed-accuracy keyboard navigation, bind to both `e.key` (semantic glyph) and `e.code` (physical key location) to ensure universal keyboard layout compatibility.

## B-002 — Guest Session Reset Cookie Re-Attachment & Blank View Desynchronization
- **Observed Behavior**: In Fast Mode, clicking "Reset" cleared `localStorage`, but the browser re-sent the existing `humark_session_id` cookie on `POST /api/sessions`. The backend returned the completed session instead of minting a new one. `getNextChallenge()` then returned `round_completed: true` with `id: null`. In `GamePage.tsx`, `scorecard` was null while `challenge.round_completed` was true, leaving the viewport completely blank and desynchronizing view toggling.
- **Design Vulnerability**: Relying on client-side `localStorage` clearing alone while an ambient HTTP cookie persisted session identity, coupled with an idempotent `POST /api/sessions` endpoint that retained existing sessions, and a frontend rendering branch that lacked fallback UI when a round completed without a pre-loaded scorecard.
- **Structural Resolution**: Implemented `create_new_session(db)` and `POST /api/sessions/reset` to unconditionally mint a fresh session with new UUID and overwrite response cookies/headers (`humark_session_id`, `X-Session-ID`). Updated frontend `resetSession()` to expire `document.cookie` (`max-age=0`), clear `localStorage`, call `/api/sessions/reset`, and store the new ID. Added fallback UI in `GamePage.tsx` with a clean "Round Completed!" prompt and scorecard toggle so the viewport never renders empty.
- **Design Heuristic**: For state reset flows involving hybrid persistence (localStorage + HTTP cookies), expose an explicit server-side reset primitive that unconditionally supersedes ambient credentials, and guarantee exhaustive fallback rendering coverage for compound component state branches.
