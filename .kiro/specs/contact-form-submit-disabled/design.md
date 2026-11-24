# Contact Form Submit Button Stuck Disabled Bugfix Design

## Overview

The contact form's submit button is permanently disabled because `assets/js/contact.js` runs top-level DOM queries (`document.querySelector`) synchronously. If `#contact-form` is absent from the DOM at execution time, `form.querySelector(...)` throws a `TypeError` on the next line, halting all further execution. The final `submitButton.disabled = false` line never runs, leaving the button (which is hardcoded `disabled` in the HTML) permanently disabled. The fix wraps the entire script body in a null-guard block so that if either `form` or `submitButton` is missing, the script logs a warning and exits cleanly rather than throwing.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug — `document.querySelector("#contact-form")` returns `null` at script execution time, causing a `TypeError` on `form.querySelector(...)` and preventing all further code from running.
- **Property (P)**: The desired behavior when both elements exist — `submitButton.disabled` is set to `false` after the script initialises, and the submit handler is attached correctly.
- **Preservation**: All existing form-submission logic (validation, fetch call, error handling, re-enable on completion) must remain unchanged by the fix.
- **contact.js**: `assets/js/contact.js` — the script that attaches the submit listener and toggles button state.
- **submitButton**: The `<button type="submit">` inside `#contact-form`. Hardcoded `disabled` in the HTML; must be enabled by the script.
- **DOMContentLoaded**: Browser event that fires once the HTML document is fully parsed, guaranteeing all elements are queryable.

## Bug Details

### Bug Condition

The bug manifests when `assets/js/contact.js` executes before (or when) `#contact-form` does not exist in the DOM. The top-level `form.querySelector(...)` call throws a `TypeError` immediately, so the entire script stops — no event listener is attached and `submitButton.disabled = false` is never reached.

**Formal Specification:**
```
FUNCTION isBugCondition(context)
  INPUT: context — the DOM state at the moment contact.js executes
  OUTPUT: boolean

  form := document.querySelector("#contact-form")
  RETURN form IS null
         OR form.querySelector('button[type="submit"]') IS null
END FUNCTION
```

### Examples

- **Script loads before DOM is ready** (no `defer`, inline `<script>`): `form` is `null`; `form.querySelector(...)` throws; button stays disabled permanently.
- **`#contact-form` element is missing from the page**: same crash path as above.
- **`<button type="submit">` removed or renamed inside the form**: `form` is non-null but `submitButton` is `null`; `submitButton.disabled = false` throws later; event listener is not reliably attached.
- **Happy path — both elements present and `defer` is in effect**: no crash, button is enabled. This is the only scenario that currently works.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Submitting the form with all fields filled sends a POST request to the API and shows a success message.
- Submitting with empty/whitespace-only fields shows the validation error without making a network request.
- The button is disabled and shows "Sending…" while a request is in flight, then re-enabled when the request completes (success or failure).
- The status message area is cleared on successful script initialisation.
- Rate-limit (429) and bad-request (400) API errors display their respective messages.

**Scope:**
All inputs that do NOT involve `#contact-form` or its submit button (e.g., other page interactions, other scripts) are completely unaffected by this fix. Within `contact.js`, every line of logic after the guard block remains identical to the original.

## Hypothesized Root Cause

Based on the bug description, the most likely issues are:

1. **No null-check on `form`**: The script calls `form.querySelector(...)` on the very next line after querying `form`, with no guard. If `form` is `null`, this is an unconditional crash.

2. **No null-check on `submitButton`**: Even if `form` exists, if the button is absent or misidentified, `submitButton.disabled = false` at the bottom of the file will throw.

3. **Script execution order risk**: Although the `<script>` tag uses `defer`, any future change removing `defer` (or inlining the script) would reproduce the bug. A `DOMContentLoaded` guard provides defence-in-depth independent of the `defer` attribute.

4. **Hardcoded `disabled` in HTML**: The button is `disabled` by default in markup, making a silent script failure invisible — there is no visual indication that initialisation failed.

## Correctness Properties

Property 1: Bug Condition - Null Guard Prevents Crash and Logs Warning

_For any_ page-load context where `isBugCondition` returns true (i.e., `#contact-form` or its submit button is absent from the DOM), the fixed `contact.js` SHALL exit cleanly with a `console.warn` message and SHALL NOT throw a `TypeError`, leaving no uncaught exception in the console.

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation - Normal Initialisation Unchanged

_For any_ page-load context where `isBugCondition` returns false (both `#contact-form` and its submit button exist), the fixed `contact.js` SHALL produce exactly the same observable behaviour as the original: `submitButton.disabled` is set to `false`, the status message is cleared, and the submit event listener is attached with identical logic.

**Validates: Requirements 3.1, 3.2, 3.3**

## Fix Implementation

### Changes Required

**File**: `assets/js/contact.js`

**Specific Changes**:

1. **Wrap body in a null-guard block**: After querying `form` and `submitButton`, add an early-exit guard:
   ```js
   if (!form || !submitButton) {
     console.warn("contact.js: required elements not found — form submission disabled.");
     return; // or just don't attach anything
   }
   ```
   Because the file is not currently inside a function, the cleanest approach is to wrap the entire script body (after the `API_URL` constant) in a `DOMContentLoaded` listener, which also provides the DOM-timing guarantee:
   ```js
   document.addEventListener("DOMContentLoaded", () => {
     const form = document.querySelector("#contact-form");
     const submitButton = form && form.querySelector('button[type="submit"]');
     const statusMessage = document.querySelector("#contact-status");

     if (!form || !submitButton) {
       console.warn("contact.js: #contact-form or its submit button not found.");
       return;
     }
     // … rest of existing logic unchanged …
   });
   ```

2. **Move variable declarations inside the callback**: `form`, `submitButton`, `statusMessage`, and `submitting` all move inside the `DOMContentLoaded` callback — no logic changes.

3. **Keep all existing logic identical**: The `submit` event listener body, fetch call, error handling, and final `submitButton.disabled = false` line remain byte-for-byte equivalent.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behaviour.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the crash BEFORE implementing the fix. Confirm the root cause is the missing null-check.

**Test Plan**: Load `contact.js` in a JSDOM environment where `#contact-form` is absent and assert that a `TypeError` is thrown. Run on UNFIXED code to confirm the failure.

**Test Cases**:
1. **Missing form element**: Load script with no `#contact-form` in DOM (will throw `TypeError` on unfixed code).
2. **Missing submit button**: Load script with `#contact-form` present but no `<button type="submit">` inside it (will throw on `submitButton.disabled` on unfixed code).
3. **Both elements absent**: Load script on a completely empty document (will throw on unfixed code).
4. **Normal DOM present**: Load script with correct DOM (should pass on both unfixed and fixed code — confirms the happy path is not broken).

**Expected Counterexamples**:
- `TypeError: Cannot read properties of null (reading 'querySelector')` thrown at line 5 of the unfixed file when form is null.
- Possible causes: no null-check, top-level synchronous DOM access.

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed script exits cleanly without throwing.

**Pseudocode:**
```
FOR ALL context WHERE isBugCondition(context) DO
  result := executeContactJS(context)
  ASSERT no TypeError thrown
  ASSERT console.warn was called
  ASSERT submitButton.disabled remains true (button not erroneously enabled)
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed script produces the same observable behaviour as the original.

**Pseudocode:**
```
FOR ALL context WHERE NOT isBugCondition(context) DO
  ASSERT contactJS_original(context).buttonEnabled = contactJS_fixed(context).buttonEnabled
  ASSERT contactJS_original(context).listenerAttached = contactJS_fixed(context).listenerAttached
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because it can generate many combinations of form field states and submission scenarios, catching regressions that targeted unit tests might miss.

**Test Plan**: Observe behaviour on UNFIXED code first for the happy-path DOM, then write tests capturing that behaviour.

**Test Cases**:
1. **Button enabled after init**: Verify `submitButton.disabled === false` after script runs with correct DOM.
2. **Submit listener fires**: Verify the `submit` event listener calls `fetch` when all fields are filled.
3. **Validation still blocks empty fields**: Verify empty-field submission does not call `fetch`.
4. **Button re-enabled after fetch completes**: Verify `submitButton.disabled === false` in `finally` block after a mock fetch resolves or rejects.

### Unit Tests

- Test that the script does not throw when `#contact-form` is absent.
- Test that the script does not throw when the submit button is absent.
- Test that `submitButton.disabled` is `false` after script runs with correct DOM.
- Test that submitting with an empty field sets the correct status message text.

### Property-Based Tests

- Generate random combinations of missing/present form elements and verify no `TypeError` is thrown in any case.
- Generate random sets of filled/empty contact fields and verify that only fully-filled forms trigger a `fetch` call.
- Generate random fetch response codes (200, 400, 429, 500) and verify `submitButton` is always re-enabled in `finally`.

### Integration Tests

- Full page load of `index.html` in a headless browser — verify button is enabled and form submits successfully to a mocked API endpoint.
- Full page load with the form element removed — verify no uncaught console error appears.
- Submit form, simulate network timeout — verify button is re-enabled and appropriate error message shown.
