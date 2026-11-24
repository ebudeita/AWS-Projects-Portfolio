# Implementation Plan

## Task Dependency Graph

```json
{
  "waves": [
    ["1", "2"],
    ["3.1"],
    ["3.2"],
    ["3.3"],
    ["3.4"],
    ["3.5", "3.6"],
    ["3.7", "3.8"],
    ["4"]
  ]
}
```

- [ ] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Deploy Step Parse Errors and Missing Uploads
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bugs exist
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples demonstrating the four confirmed bugs on the unfixed script
  - **Scoped PBT Approach**: Scope each sub-case to concrete failing inputs for reproducibility
  - Test 1a: Call `parser.parse_args(["--dry-run"])` on the unfixed `deploy.py` — assert `SystemExit(2)` is raised (undefined flag)
  - Test 1b: Call `parser.parse_args([])` on the unfixed `deploy.py` — assert `SystemExit(2)` is raised (missing required `--bucket`)
  - Test 1c: Mock S3 `head_object` to return 404, run unfixed script with valid `--bucket` and `--source`, assert `s3.put_object` was **never** called (preview-only behavior)
  - Test 1d: Run unfixed script end-to-end with mocked S3, assert `GITHUB_OUTPUT` file contains no `changed=` line after execution
  - Run all four tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (this is correct — it proves the bugs exist)
  - Document counterexamples found (e.g., `SystemExit(2)` from argparse, `put_object` call count = 0)
  - Mark task complete when tests are written, run, and failures are documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Identical-File Skip, Extension Filter, and pinegrow Exclusion
  - **IMPORTANT**: Follow observation-first methodology
  - Observe: on unfixed code, when local MD5 matches S3 ETag, the SKIP branch executes and `unchanged` increments — no `put_object` call
  - Observe: files with extensions outside `EXTENSIONS` and not named `robots.txt` are silently ignored by the unfixed script
  - Observe: `pinegrow.json` is excluded from processing regardless of content
  - Write property-based test: for all source directories containing files whose MD5 equals their S3 ETag, assert no upload is made and `unchanged` counter increments
  - Write property-based test: for randomly generated file extension sets, assert only files in `EXTENSIONS` or named `robots.txt` are processed
  - Write property-based test: assert `pinegrow.json` is never passed to any upload path regardless of file content
  - Run all preservation tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 3. Fix the CI/CD deployment pipeline

  - [ ] 3.1 Add `CONTENT_TYPES` and `CACHE_CONTROL` module-level dicts to `scripts/deploy.py`
    - Add `CONTENT_TYPES` mapping: `.html` → `text/html; charset=utf-8`, `.css` → `text/css; charset=utf-8`, `.js` → `application/javascript; charset=utf-8`, `.json` → `application/json; charset=utf-8`, `.xml` → `application/xml; charset=utf-8`, `.ico` → `image/x-icon`, `.png` → `image/png`, `.jpg` → `image/jpeg`, `.jpeg` → `image/jpeg`, `.gif` → `image/gif`, `.svg` → `image/svg+xml`, `.webp` → `image/webp`, `.woff` → `font/woff`, `.woff2` → `font/woff2`, `.ttf` → `font/ttf`, `robots.txt` → `text/plain; charset=utf-8`
    - Add `CACHE_CONTROL` mapping: `.html` → `no-cache`; all other extensions → `public, max-age=31536000, immutable`
    - _Bug_Condition: isBugCondition(input) where input.script.uploadsFiles == false (no ContentType/CacheControl set on uploads)_
    - _Expected_Behavior: upload_file sets ContentType and CacheControl from these dicts on every s3.put_object call_
    - _Requirements: 2.1, 2.2_

  - [ ] 3.2 Add `upload_file(s3, bucket, key, path)` helper function to `scripts/deploy.py`
    - Read file bytes from `path`
    - Look up `ContentType` from `CONTENT_TYPES` using the file extension (or filename for `robots.txt`)
    - Look up `CacheControl` from `CACHE_CONTROL` using the file extension (default to immutable for unknown extensions)
    - Call `s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type, CacheControl=cache_control)`
    - _Bug_Condition: isBugCondition(input) where input.script.uploadsFiles == false (no s3.put_object calls exist)_
    - _Expected_Behavior: expectedBehavior — every new, changed, or unverified file is uploaded via this helper with correct metadata_
    - _Preservation: existing MD5/ETag comparison logic unchanged; helper is additive_
    - _Requirements: 2.1, 2.4, 2.5_

  - [ ] 3.3 Replace all `print(f"WOULD UPLOAD...")` statements with `upload_file(...)` calls in `scripts/deploy.py`
    - In the 404 branch (new file): replace `print(f"WOULD UPLOAD ...")` with `upload_file(s3, bucket, key, path)`
    - In the differing-ETag branch (changed file): replace `print(f"WOULD UPLOAD ...")` with `upload_file(s3, bucket, key, path)`
    - In the non-MD5-ETag branch (unverified): replace `print(f"WOULD UPLOAD ...")` with `upload_file(s3, bucket, key, path)`
    - Keep existing counters (`changed += 1`, `unverified += 1`) in place
    - _Bug_Condition: isBugCondition(input) where input.script.uploadsFiles == false_
    - _Expected_Behavior: expectedBehavior — script uploads every file where local MD5 differs from S3 ETag or file is new_
    - _Preservation: SKIP branch for identical MD5/ETag is untouched; unchanged counter still increments_
    - _Requirements: 2.1, 2.4, 2.5, 3.1, 3.2_

  - [ ] 3.4 Write `changed` output to `$GITHUB_OUTPUT` in `scripts/deploy.py`
    - After the upload loop, read `os.environ["GITHUB_OUTPUT"]`
    - Open the file in append mode
    - Write `changed=true\n` if `changed + unverified > 0`, else `changed=false\n`
    - _Bug_Condition: isBugCondition(input) where input.script.writesGithubOutput == false_
    - _Expected_Behavior: expectedBehavior — GITHUB_OUTPUT contains "changed=true" when files were uploaded, "changed=false" otherwise_
    - _Preservation: CloudFront invalidation step condition `steps.s3_deploy.outputs.changed == 'true'` is unchanged_
    - _Requirements: 2.2, 2.3, 3.6_

  - [ ] 3.5 Update summary output and module docstring in `scripts/deploy.py`
    - Rename summary label `"Would upload"` → `"Uploaded"` in the summary print block
    - Remove the `"DRY RUN ONLY - no files uploaded or deleted."` line
    - Replace it with `"Deployment complete."`
    - Update the module docstring from `"Preview checksum-based..."` to `"Checksum-based deployment..."`
    - _Requirements: 2.1_

  - [ ] 3.6 Fix the workflow invocation in `.github/workflows/deploy.yml`
    - Rename step: `Preview checksum-based S3 deployment` → `Deploy changed files to S3`
    - Change run command: `python scripts/deploy.py --dry-run` → `python scripts/deploy.py --bucket "$S3_BUCKET"`
    - Remove the `echo "changed=false" >> "$GITHUB_OUTPUT"` line (script now writes this)
    - Keep `set -euo pipefail`, `env: S3_BUCKET: ${{ vars.S3_BUCKET }}`, and `id: s3_deploy` unchanged
    - _Bug_Condition: isBugCondition(input) where "--dry-run" IN input.args OR "--bucket" NOT IN input.args_
    - _Expected_Behavior: expectedBehavior — argparse accepts `--bucket "$S3_BUCKET"` and the script reaches the upload loop_
    - _Preservation: all other workflow steps (checkout, Python setup, AWS credentials, file prep, CloudFront invalidation) are untouched_
    - _Requirements: 2.1, 3.3, 3.4, 3.6_

  - [ ] 3.7 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Deploy Step Parse Errors and Missing Uploads
    - **IMPORTANT**: Re-run the SAME tests from task 1 — do NOT write new tests
    - The tests from task 1 encode the expected behavior
    - When these tests pass, they confirm the fixed script accepts `--bucket`, rejects unknown flags, calls `s3.put_object` for new/changed files, and writes `changed=` to `GITHUB_OUTPUT`
    - Run the four bug condition tests from step 1 against the FIXED code
    - **EXPECTED OUTCOME**: Tests PASS (confirms all four bugs are fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ] 3.8 Verify preservation tests still pass
    - **Property 2: Preservation** - Identical-File Skip, Extension Filter, and pinegrow Exclusion
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run all preservation property tests from step 2 against the FIXED code
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions in SKIP logic, extension filter, or pinegrow exclusion)
    - Confirm all tests still pass after fix (no regressions)

- [ ] 4. Checkpoint — Ensure all tests pass
  - Run the full test suite (unit tests, property-based tests) and confirm every test passes
  - Confirm the bug condition exploration tests (Property 1) pass on the fixed code
  - Confirm the preservation property tests (Property 2) pass on the fixed code
  - Ensure all tests pass; ask the user if any questions arise
