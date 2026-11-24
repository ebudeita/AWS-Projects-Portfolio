# Bugfix Requirements Document

## Introduction

The CI/CD deployment pipeline for the AWS portfolio static website always fails at the
"Preview checksum-based S3 deployment" step. The workflow calls `python scripts/deploy.py --dry-run`,
but `deploy.py` neither recognises `--dry-run` as a valid flag nor receives the required `--bucket`
argument, causing argparse to exit with an error before any S3 work occurs. Because the step fails,
the `changed` output is never written correctly, so the downstream CloudFront cache-invalidation step
is permanently skipped. The fix converts the script from a preview-only tool into a real deployer that
uploads changed files and signals the workflow whether a CloudFront invalidation is needed.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the workflow calls `python scripts/deploy.py --dry-run` without a `--bucket` argument
    THEN the system exits immediately with `error: the following arguments are required: --bucket`
    before reading or comparing any files.

1.2 WHEN the workflow calls `python scripts/deploy.py --dry-run` with `--bucket` supplied
    THEN the system exits with `error: unrecognized arguments: --dry-run` because the flag is
    not defined in argparse, preventing the script from running.

1.3 WHEN the deploy step exits with a non-zero code due to either argparse error
    THEN the workflow step fails and the subsequent `echo "changed=false"` line is never reached,
    so `changed` output is never set and CloudFront invalidation is unconditionally skipped.

1.4 WHEN files in the `deploy/` staging directory differ from the objects in S3
    THEN the system never uploads those changed files because `deploy.py` only prints a preview
    and contains no `s3.upload_file` or equivalent call.

### Expected Behavior (Correct)

2.1 WHEN the workflow calls `python scripts/deploy.py --bucket "$S3_BUCKET"` without `--dry-run`
    THEN the system SHALL accept the invocation, compare local checksums against S3 ETags, upload
    every file that is new or changed, and exit with code 0.

2.2 WHEN at least one file is uploaded during the deploy step
    THEN the system SHALL write `changed=true` to `$GITHUB_OUTPUT` so the CloudFront invalidation
    step is triggered.

2.3 WHEN no files differ from their S3 counterparts during the deploy step
    THEN the system SHALL write `changed=false` to `$GITHUB_OUTPUT` and the CloudFront invalidation
    step SHALL be skipped.

2.4 WHEN `deploy.py` encounters a file that does not yet exist in S3 (HTTP 404 from `head_object`)
    THEN the system SHALL upload that file to S3 and count it as a changed file.

2.5 WHEN `deploy.py` encounters a file whose local MD5 differs from the S3 ETag
    THEN the system SHALL upload that file to S3 and count it as a changed file.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a file's local MD5 matches the S3 ETag exactly
    THEN the system SHALL CONTINUE TO skip that file and not re-upload it, preserving the
    checksum-based deduplication behaviour.

3.2 WHEN the S3 ETag for an object is not a plain MD5 hex string (e.g. multipart upload ETag)
    THEN the system SHALL CONTINUE TO log the file as UNVERIFIED and upload it to ensure
    correctness, consistent with the existing unverified-upload intent.

3.3 WHEN the `--source` argument is provided explicitly
    THEN the system SHALL CONTINUE TO read files from that directory instead of the default
    `deploy/` directory.

3.4 WHEN the source directory does not exist
    THEN the system SHALL CONTINUE TO exit with an argparse error identifying the missing
    directory, preventing silent no-ops.

3.5 WHEN files outside the defined EXTENSIONS set are present in the staging directory
    THEN the system SHALL CONTINUE TO ignore them and not upload them to S3.

3.6 WHEN the CloudFront invalidation step runs
    THEN the system SHALL CONTINUE TO invalidate `/*` using the `CLOUDFRONT_DISTRIBUTION_ID`
    workflow variable, unchanged from the current workflow definition.
