# Humark Confirmed Behavioral Defect Log

This document records confirmed behavioral defects discovered during working-run verification or user testing.

## B-001 — Physical Number Key Input Failure on Challenge Card
- **Observed Behavior**: User reported key '1' does not register selection for Option A while 'A' worked.
- **Design Vulnerability**: Coupling keyboard shortcuts solely to `KeyboardEvent.key` rather than checking hardware-agnostic `KeyboardEvent.code` (`Digit1`, `Numpad1`).
- **Structural Resolution**: Check both character value (`e.key`) and physical key code (`e.code`) for top-row numbers, numpad numbers, and character letters (`Digit1`/`Digit2`, `Numpad1`/`Numpad2`, `KeyA`/`KeyB`).
- **Design Heuristic**: For gaming and speed-accuracy keyboard navigation, bind to both `e.key` (semantic glyph) and `e.code` (physical key location) to ensure universal keyboard layout compatibility.

