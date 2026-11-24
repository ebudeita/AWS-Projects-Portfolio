# CI/CD Pipeline Deploy Fix Bugfix Design

## Overview

The GitHub Actions deployment pipeline for this AWS portfolio static website has never actually deployed anything. The workflow step that is supposed to upload changed files to S3 fails immediately in two ways: `--dry-run` is passed but never defined in `argparse`, causing an immediate parse error, and `--bucket` is required by the script but never provided by the workflow. Even if neither argument problem existed, the script only prints a preview and writes nothing to S3. Additionally, the step hardcodes `changed=false` as its output regardless of what the script does, so the CloudFront cache invalidation never fires.

The fix converts `deploy.py` from a preview-only script into a real deployer that uploads new and changed files using checksum comparison, writes `changed=true/false` to `$GITHUB_OUTPUT`, and sets correct `Content-Type` and `Cache-Control` headers on each upload. The workflow step is updated to pass `--bucket` and remove the now-redundant hardcoded output line.

## Glossary

- **Bug_Condition (C)**: The set of CI/CD pipeline runs where the deploy step is invoked, which covers every push to `main` that touches a tracked file extension and every `workflow_dispatch` trigger.
- **Property (P)**: The desired behavior — the deploy step uploads all new and changed files to S3, skips identical files, and writes the correct `changed` output so the CloudFront invalidation fires when needed.
- **Preservation**: All existing pipeline behavior outside the deploy step must remain unchanged: checkout, Python setup, AWS credential configuration, the `Prepare website files` step, and the CloudFront invalidation step logic.
- **`deploy.py`**: The script at `scripts/deploy.py` responsible for comparing local files against S3 objects by MD5/ETag and uploading differences.
- **`deploy.yml`**: The workflow at `.github/workflows/deploy.yml` that orchestrates the full CI/CD pipeline.
- **ETag**: The S3 object metadata field. For non-multipart uploads, S3 sets it to the MD5 hex digest of the object body, enabling cheap change detection without re-downloading the file.
- **`GITHUB_OUTPUT`**: The environment file path where GitHub Actions steps write `key=value` pairs to pass data between steps.

## Bug Details

### Bug Condition

The bug manifests on every pipeline run that reaches the `Preview checksum-based S3 deployment` step. The step invokes `python scripts/deploy.py --dry-run`, which fails at argument parsing before any S3 logic runs. Even if the argument errors were silently ignored, the script contains no upload calls and always exits without writing to `$GITHUB_OUTPUT`. The hardcoded `echo "changed=false"` that follows ensures the CloudFront step is permanently suppressed.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type PipelineRun
  OUTPUT: boolean

  RETURN input.step == "s3_deploy"
         AND (
               "--dry-run" IN input.args          // undefined flag → argparse error
               OR "--bucket" NOT IN input.args    // required flag absent → argparse error
               OR input.script.uploadsFiles == false  // no s3.put_object / upload_file calls
               OR input.script.writesGithubOutput == false  // no GITHUB_OUTPUT write
             )
END FUNCTION
```

### Examples

- **Trigger**: push to `main` modifying `index.html`. Expected: script uploads `index.html` to S3, writes `changed=true`, CloudFront invalidation fires. Actual: `argparse` exits with error 2 on `--dry-run`, step fails, no upload, no invalidation.
- **Trigger**: `workflow_dispatch` with no changed files in S3. Expected: script compares all local files against S3, skips identical ones, writes `changed=false`. Actual: same parse error, step fails.
- **Trigger**: First-ever deploy after S3 bucket is empty. Expected: every file is uploaded (all are new), `changed=true` written. Actual: parse error, nothing uploaded.
- **Edge case**: File whose S3 ETag is not a plain MD5 (multipart upload). Expected: file is uploaded (UNVERIFIED path), counts toward `changed`. Actual: would never be reached under current code.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- All workflow steps before `s3_deploy` (checkout, Python setup, dependency install, AWS credential configuration, identity verification, file preparation) must continue to run exactly as they do today.
- The CloudFront invalidation step must continue to fire if and only if `steps.s3_deploy.outputs.changed == 'true'` — its condition and AWS CLI command are unchanged.
- The `EXTENSIONS` filter and `pinegrow.json` exclusion in `deploy.py` must remain in effect.
- The MD5-vs-ETag checksum comparison logic (SKIP for identical, upload for changed, upload for unverified ETag) must remain semantically the same — only the action taken changes from "print WOULD UPLOAD" to actually uploading.
- Human-readable log lines (`SKIP (identical)`, `UPLOADED (new)`, `UPLOADED (changed)`, `UNVERIFIED UPLOADED`) must still be printed.
- The script must exit 0 on a clean run and non-zero on unexpected S3 errors.

**Scope:**
All pipeline runs that do not involve the `s3_deploy` step are completely unaffected. Within the step, all logic paths that do not touch the four bugs (undefined flag, missing bucket arg, absent upload calls, absent GITHUB_OUTPUT write) are preserved as-is.

## Hypothesized Root Cause

Based on the bug description and source inspection, the causes are confirmed and mechanical rather than speculative:

1. **Undefined `--dry-run` flag**: `argparse` is strict; passing an unrecognized argument causes an immediate `SystemExit(2)`. The flag was added to the workflow call but never registered with `parser.add_argument`.

2. **Missing `--bucket` argument in workflow**: `args.bucket` is `required=True`. The workflow invocation `python scripts/deploy.py --dry-run` passes no `--bucket`, so even if `--dry-run` were defined, the parser would still exit with an error about the missing required argument.

3. **No upload calls in script body**: The script was written as a preview/dry-run tool. Every code path that would upload a file instead prints `WOULD UPLOAD`. There are no `s3.upload_file` or `s3.put_object` calls anywhere in the script.

4. **No `GITHUB_OUTPUT` write in script**: The script never reads `os.environ["GITHUB_OUTPUT"]` or writes `changed=true/false` to it. The workflow compensates with a hardcoded `echo "changed=false"`, which permanently prevents the CloudFront invalidation from ever firing, even after the upload logic is added.

## Correctness Properties

Property 1: Bug Condition - Deploy Step Uploads Files and Writes Output

_For any_ pipeline run where `isBugCondition` returns true (the deploy step is invoked), the fixed `deploy.py` script SHALL successfully parse `--bucket`, upload every file where the local MD5 differs from the S3 ETag (or the file is new, or the ETag is not a plain MD5), and write `changed=true` to `$GITHUB_OUTPUT` when at least one file was uploaded, or `changed=false` when all files were skipped as identical.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

Property 2: Preservation - Non-Deploy Pipeline Behavior Unchanged

_For any_ pipeline execution path where `isBugCondition` returns false (steps other than `s3_deploy`, or runs where no tracked files changed), the fixed workflow and script SHALL produce exactly the same behavior as the original code, preserving checkout, build preparation, AWS credential handling, the CloudFront invalidation condition, the EXTENSIONS filter, the pinegrow.json exclusion, and the MD5/ETag comparison logic.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

## Fix Implementation

### Changes Required

Assuming the root cause analysis is correct (all four causes are confirmed by direct source inspection):

**File**: `scripts/deploy.py`

**Specific Changes**:

1. **Remove `--dry-run` from the invocation path**: The flag was never registered. No `add_argument` call is needed; it simply must not appear in the workflow invocation.

2. **Add `CONTENT_TYPES` mapping**: A module-level dict maps each tracked extension (and `robots.txt`) to the correct MIME type with charset where applicable. Used as the `ContentType` kwarg on every upload.

3. **Add `CACHE_CONTROL` mapping**: A module-level dict maps `.html` to `no-cache` and a `DEFAULT_CACHE` constant to `public, max-age=31536000, immutable` for all other extensions. Used as the `CacheControl` kwarg on every upload.

4. **Add `upload_file` helper function**: Encapsulates the `s3.put_object` call, reads file bytes, sets `ContentType` and `CacheControl`, and prints the appropriate log line (`UPLOADED (new)`, `UPLOADED (changed)`, `UNVERIFIED UPLOADED`).

5. **Replace `print(f"WOULD UPLOAD ...")` with actual upload calls**: In the 404 branch (new file), the changed-ETag branch, and the unverified-ETag branch, call `upload_file` instead of printing a preview message. Keep `unchanged += 1` / `changed += 1` / `unverified += 1` counters.

6. **Write `changed` to `$GITHUB_OUTPUT`**: After the loop, open the file at `os.environ["GITHUB_OUTPUT"]` in append mode and write `changed=true\n` if `changed + unverified > 0`, else `changed=false\n`. Unverified files are uploaded, so they count as changed.

7. **Update module docstring and summary print**: Change `"DRY RUN ONLY - no files uploaded or deleted."` to `"Deployment complete."` and update the summary labels from `"Would upload"` to `"Uploaded"`.

**File**: `.github/workflows/deploy.yml`

**Specific Changes**:

1. **Rename the step**: Change `name: Preview checksum-based S3 deployment` to `name: Deploy changed files to S3`.

2. **Fix the `run` command**: Replace `python scripts/deploy.py --dry-run` with `python scripts/deploy.py --bucket "$S3_BUCKET"`. The `S3_BUCKET` env var is already set on the step via `env: S3_BUCKET: ${{ vars.S3_BUCKET }}`.

3. **Remove the hardcoded output line**: Delete `echo "changed=false" >> "$GITHUB_OUTPUT"`. The script now writes this itself.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate each bug on the unfixed code to confirm the root cause analysis, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bugs BEFORE implementing the fix. Confirm root cause analysis. If any finding differs from the hypothesis, re-hypothesize before proceeding.

**Test Plan**: Write unit tests that invoke `main()` (or the argument parser directly) with the broken workflow arguments, mock the S3 client to avoid real AWS calls, and assert on the failures observed. Run these tests against the UNFIXED script.

**Test Cases**:
1. **Argparse rejects `--dry-run`**: Call `parser.parse_args(["--dry-run"])` on the unfixed script — expect `SystemExit(2)` (will fail on unfixed code).
2. **Argparse rejects missing `--bucket`**: Call `parser.parse_args([])` — expect `SystemExit(2)` for missing required argument (will fail on unfixed code).
3. **No upload on new file**: Mock S3 `head_object` to return 404, run the unfixed script with valid `--bucket` and `--source`, assert that `s3.put_object` was never called (will confirm the preview-only behavior on unfixed code).
4. **`GITHUB_OUTPUT` not written**: Run unfixed script end-to-end with a mocked S3, assert `GITHUB_OUTPUT` file is empty or not written (will confirm on unfixed code).

**Expected Counterexamples**:
- `SystemExit(2)` from argparse when `--dry-run` is present without being defined.
- `SystemExit(2)` from argparse when `--bucket` is absent.
- `s3.put_object` call count equals zero even when files differ.
- `GITHUB_OUTPUT` file contains no `changed=` line after script run.

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed script produces the expected behavior.

**Pseudocode:**
```
FOR ALL pipelineRun WHERE isBugCondition(pipelineRun) DO
  result := deploy_fixed(pipelineRun)
  ASSERT result.exitCode == 0
  ASSERT result.s3PutObjectCallCount >= result.newFiles + result.changedFiles + result.unverifiedFiles
  ASSERT result.githubOutput CONTAINS "changed=true" OR "changed=false"
  IF result.newFiles + result.changedFiles + result.unverifiedFiles > 0 THEN
    ASSERT result.githubOutput CONTAINS "changed=true"
  ELSE
    ASSERT result.githubOutput CONTAINS "changed=false"
  END IF
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed script and workflow produce the same result as the original.

**Pseudocode:**
```
FOR ALL pipelineRun WHERE NOT isBugCondition(pipelineRun) DO
  ASSERT deploy_original(pipelineRun) == deploy_fixed(pipelineRun)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many random file sets and S3 states automatically.
- It catches edge cases (empty source dir, all files identical, mixed ETag formats) that manual tests miss.
- It provides strong guarantees that the EXTENSIONS filter, pinegrow.json exclusion, and MD5 comparison logic are unchanged.

**Test Plan**: Observe behavior on UNFIXED code for identical-file paths (SKIP branch), then write property-based tests that assert the fixed script produces the same SKIP decisions for all inputs where `local_md5 == etag`.

**Test Cases**:
1. **SKIP preservation**: For files where local MD5 equals S3 ETag, assert no upload is made and `unchanged` counter increments — same as unfixed behavior.
2. **EXTENSIONS filter preservation**: Files with extensions outside `EXTENSIONS` and not named `robots.txt` must still be excluded from processing.
3. **`pinegrow.json` exclusion preservation**: A file named `pinegrow.json` must never be uploaded regardless of its content.
4. **CloudFront condition preservation**: The `if: steps.s3_deploy.outputs.changed == 'true'` condition in the workflow must still gate the CloudFront step correctly after the script writes output.

### Unit Tests

- Test argument parsing accepts `--bucket` and `--source`, rejects unknown flags.
- Test `md5_file` returns correct hex digest for known inputs.
- Test `upload_file` calls `s3.put_object` with correct `Key`, `ContentType`, and `CacheControl` for each extension.
- Test the 404 branch (new file) triggers an upload and increments `changed`.
- Test the matching-ETag branch skips upload and increments `unchanged`.
- Test the differing-ETag branch triggers an upload and increments `changed`.
- Test the non-MD5-ETag branch triggers an upload and increments `unverified`.
- Test `GITHUB_OUTPUT` receives `changed=true` when at least one file was uploaded.
- Test `GITHUB_OUTPUT` receives `changed=false` when all files were skipped.

### Property-Based Tests

- Generate random sets of local files and S3 states; assert that files with matching MD5/ETag are always skipped (preservation of SKIP logic).
- Generate random file extensions; assert that only files in `EXTENSIONS` or named `robots.txt` are processed (preservation of filter logic).
- Generate random collections of new and changed files; assert `changed=true` is written to `GITHUB_OUTPUT` whenever the uploaded count is positive.
- Generate collections where all files are identical; assert `changed=false` is written and `s3.put_object` is never called.

### Integration Tests

- Run the fixed `deploy.py` against a real (or localstack) S3 bucket with a known set of files; verify objects appear in the bucket with correct metadata.
- Trigger the full workflow via `workflow_dispatch` on a test branch; verify the `s3_deploy` step exits 0 and that `changed` output propagates correctly to the CloudFront step.
- Verify that a second identical run produces no uploads and writes `changed=false`.
