# Implementation Plan

## Overview

Both fixes are already applied to the codebase. Tasks 1–4 write property-based tests against the fixed code to confirm each bug is resolved and existing behaviour is preserved. Tasks 5–9 cover the manual browser smoke test, CI/CD pipeline confirmation, and the CORS clean-up step in AWS API Gateway.

## Task Dependency Graph

```json
{
  "waves": [
    { "wave": 1, "tasks": ["1", "2", "3", "4"] },
    { "wave": 2, "tasks": ["5", "6", "7", "8"] },
    { "wave": 3, "tasks": ["9"] }
  ]
}
```

## Tasks

> **Context**: Both fixes are already applied to the codebase. Tasks 1–2 write tests
> against the fixed code to confirm the bugs are resolved and behaviour is preserved.
> Tasks 3–5 cover the manual and CI/CD verification steps the user requested.

---

## Bug 1 — Contact Form Submit Button Stuck Disabled

- [ ] 1. Write bug condition exploration test (contact form)
  - **Property 1: Bug Condition** - Null-Guard Prevents Crash on Missing DOM Elements
  - **IMPORTANT**: The fix is already applied — this test SHOULD NOW PASS on the fixed code
  - **GOAL**: Confirm the bug condition is resolved; document what counterexamples would have looked like on unfixed code
  - **Scoped PBT Approach**: Scope to the two concrete failing cases: (a) `#contact-form` absent, (b) submit button absent inside the form
  - Load `contact.js` via JSDOM with `#contact-form` missing — assert no `TypeError` is thrown and `console.warn` fires (from Bug Condition in design: `isBugCondition` returns `true` when form is null)
  - Load `contact.js` via JSDOM with form present but no `<button type="submit">` — assert same clean-exit behaviour
  - Load `contact.js` on a completely empty document — assert no uncaught exception
  - **EXPECTED OUTCOME**: All three cases PASS (confirms null-guard fix works)
  - If any case fails, do NOT modify the test — investigate the fix instead
  - Document the counterexample that would have been seen on unfixed code: `TypeError: Cannot read properties of null (reading 'querySelector')` at line 5
  - _Requirements: 1.1, 1.2, 2.1_

- [ ] 2. Write preservation property tests (contact form, BEFORE any further changes)
  - **Property 2: Preservation** - Normal Initialisation and Submit Logic Unchanged
  - **IMPORTANT**: Follow observation-first methodology — run fixed code with valid DOM and observe outputs
  - Observe: `submitButton.disabled === false` after `DOMContentLoaded` fires with `#contact-form` and submit button present
  - Observe: empty-field submission sets `statusMessage.textContent` to the validation message and does NOT call `fetch`
  - Observe: `submitButton.disabled` is `true` while fetch is in flight, then `false` in `finally` block
  - Write property-based tests: for all fully-filled contact objects (`name`, `email`, `subject`, `message` all non-empty), `fetch` is called once per submit (from Preservation Requirements in design)
  - Write property-based tests: for all partially-empty contact objects, `fetch` is never called
  - Verify tests PASS on fixed code
  - **EXPECTED OUTCOME**: All preservation tests PASS (confirms no regressions in validation, fetch, error-handling, re-enable logic)
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

---

## Bug 2 — package.json `main` Field Mismatch

- [ ] 3. Write bug condition exploration test (package.json)
  - **Property 1: Bug Condition** - `main` Field Resolves to Existing File
  - **IMPORTANT**: The fix is already applied — this test SHOULD NOW PASS on the fixed code
  - **GOAL**: Confirm resolution succeeds; document what counterexample would have been seen on unfixed file
  - Assert `backend/contact/package.json["main"] === "index.mjs"` (from Bug Condition in design: `isBugCondition` returns `true` when `main !== "index.mjs"`)
  - Assert `backend/contact/index.mjs` exists on disk (file-existence check)
  - Assert `backend/contact/index.js` does NOT exist (confirms the mismatched target is gone)
  - Run Node resolution: `node -e "import('./backend/contact/index.mjs').then(() => process.exit(0))"` — assert exit code 0
  - **EXPECTED OUTCOME**: All assertions PASS (confirms `main` field now resolves correctly)
  - Document what would have been seen on unfixed file: `Error: Cannot find module './index.js'` with `MODULE_NOT_FOUND`
  - _Requirements: 1.3, 2.3_

- [ ] 4. Write preservation property tests (package.json)
  - **Property 2: Preservation** - All Other package.json Fields Unchanged
  - **IMPORTANT**: Follow observation-first methodology — read the fixed file and record all field values
  - Observe and record: `name`, `version`, `description`, `scripts`, `keywords`, `author`, `license`, `dependencies` from fixed `package.json`
  - Write tests asserting each of those fields is exactly preserved (from Preservation Requirements in design: all fields except `"main"` must remain identical)
  - Assert `Object.keys(fixed)` equals the expected set — no new fields were added or removed
  - Assert `dependencies["@aws-sdk/client-ses"]` still equals `"^3.1161.0"`
  - Verify tests PASS on fixed file
  - **EXPECTED OUTCOME**: All field-preservation tests PASS (confirms only `"main"` changed)
  - _Requirements: 3.1, 3.2 (package.json preservation requirements)_

---

## Verification and Deployment Checks

- [ ] 5. Verify contact form submit button is enabled in the browser (manual smoke test)

  - [ ] 5.1 Open `index.html` in a browser (local file server or deployed URL)
    - Confirm the **Send message** button is not greyed out and is clickable on page load
    - Open DevTools → Console — confirm no uncaught TypeErrors are present
    - _Bug_Condition: `isBugCondition` = form or button missing at execute time_
    - _Expected_Behavior: `submitButton.disabled === false` after `DOMContentLoaded`_
    - _Preservation: all submit/validation/fetch logic operates identically to original_
    - _Requirements: 2.1, 2.2, 3.1, 3.2, 3.3_

  - [ ] 5.2 Verify **Property 1: Expected Behavior** — Null Guard
    - **Property 1: Expected Behavior** - Null Guard
    - Re-run the test from task 1 (do NOT write a new test)
    - **EXPECTED OUTCOME**: PASSES — confirms null-guard fix is working
    - _Requirements: 2.1_

  - [ ] 5.3 Verify **Property 2: Preservation** — Contact Form Submit Logic
    - **Property 2: Preservation** - Contact Form Submit Logic
    - Re-run the preservation tests from task 2 (do NOT write new tests)
    - **EXPECTED OUTCOME**: PASSES — confirms no regressions in submit/validation/error-handling behaviour
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 6. Verify `package.json` `"main"` field resolves correctly

  - [ ] 6.1 Confirm `main` field value in the file
    - Run: `node -e "const p = require('./backend/contact/package.json'); console.log(p.main)"` — expected output: `index.mjs`
    - Run: `node -e "import('./backend/contact/index.mjs').then(() => console.log('ok'))"` — expected output: `ok`
    - _Bug_Condition: `main` resolves to non-existent `index.js`_
    - _Expected_Behavior: `main` resolves to existing `index.mjs`_
    - _Preservation: all other package.json fields unchanged_
    - _Requirements: 1.3, 2.3_

  - [ ] 6.2 Verify **Property 1: Expected Behavior** — `main` Field Resolves
    - **Property 1: Expected Behavior** - main Field Resolves
    - Re-run the test from task 3 (do NOT write a new test)
    - **EXPECTED OUTCOME**: PASSES — confirms `main` field points to `index.mjs`
    - _Requirements: 2.3_

  - [ ] 6.3 Verify **Property 2: Preservation** — package.json Fields Unchanged
    - **Property 2: Preservation** - package.json Fields Unchanged
    - Re-run the preservation tests from task 4 (do NOT write new tests)
    - **EXPECTED OUTCOME**: PASSES — confirms no other fields were altered
    - _Requirements: 3.1, 3.2 (package.json preservation)_

- [ ] 7. Confirm CI/CD deploy workflow picks up both changed files

  - [ ] 7.1 Verify the workflow path filter covers both changed files
    - Open `.github/workflows/deploy.yml` and confirm the `paths` trigger includes `**/*.js` and `**/*.json`
    - `assets/js/contact.js` matches `**/*.js` ✓
    - `backend/contact/package.json` matches `**/*.json` ✓
    - _Requirements: implied by deployment correctness_

  - [ ] 7.2 Confirm the workflow's file-collection step includes both files
    - The `git ls-files -z` loop in `deploy.yml` copies `*.js` and `*.json` files into the `deploy/` staging directory
    - After the deploy run, check the workflow log for both files in the checksum list
    - Confirm `sha256sum` output includes `assets/js/contact.js` and `backend/contact/package.json`

  - [ ] 7.3 Trigger the workflow and verify S3 sync and CloudFront invalidation
    - Push both changed files to the `main` branch (or trigger `workflow_dispatch`)
    - In the GitHub Actions run, confirm the `s3_deploy` step sets `changed=true`
    - Confirm the `Invalidate CloudFront cache` step runs and reports a successful invalidation

- [ ] 8. Remove local dev origin from API Gateway CORS Allow-Origin (manual AWS console step)

  - [ ] 8.1 Identify the CORS configuration on the HTTP API
    - In AWS Console → API Gateway → `eva2a9pv06` (or the named API) → CORS settings
    - Locate the `Allow-Origin` list and confirm `http://127.0.0.1:5500` is present

  - [ ] 8.2 Remove `http://127.0.0.1:5500` from Allow-Origin
    - Delete `http://127.0.0.1:5500` from the Allow-Origin list
    - Confirm only the production origin (e.g., your CloudFront/custom domain) remains
    - Save the CORS configuration

  - [ ] 8.3 Confirm production origin still works after CORS update
    - Open the contact form at the production URL and submit a test message
    - In DevTools → Network, confirm the preflight OPTIONS request returns `200` and the `Access-Control-Allow-Origin` header matches the production domain
    - Confirm the POST request also succeeds (no CORS error in console)

- [ ] 9. Checkpoint — all tests and checks pass
  - Ensure tasks 1–4 test suites all pass
  - Ensure manual smoke test (task 5.1) passes
  - Ensure CI/CD workflow run (task 7.3) completes without errors
  - Ensure CORS config (task 8) is updated and production form still works
  - Ask the user if any questions arise before closing out

## Notes

- Tests for tasks 1–4 require a JSDOM-capable test runner (e.g., Vitest with `environment: 'jsdom'` or Jest with `testEnvironment: 'jsdom'`). No build step is needed — the project deploys files directly.
- Tasks 5.1 and 8 are manual steps that cannot be automated within the repository.
- Task 7 requires the two changed files to be committed and pushed to `main` to trigger the GitHub Actions workflow. Alternatively, use `workflow_dispatch` from the Actions tab.
- The API URL (`eva2a9pv06.execute-api.us-east-1.amazonaws.com/contact`) is hardcoded in `contact.js`. When testing locally, ensure the CORS origin is configured to allow the local origin, then remove it again per task 8.
