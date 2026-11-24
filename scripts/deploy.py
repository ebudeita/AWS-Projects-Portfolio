#!/usr/bin/env python3
"""Preview checksum-based deployment to Amazon S3."""

import argparse
import hashlib
import os
import re
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

EXTENSIONS = {
    ".html", ".css", ".js", ".json", ".ico",
    ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".webp", ".woff", ".woff2", ".ttf", ".xml",
}


def md5_file(path):
    digest = hashlib.md5(usedforsecurity=False)

    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--source", default="deploy")
    args = parser.parse_args()

    source = Path(args.source).resolve()

    if not source.is_dir():
        parser.error(f"Source directory does not exist: {source}")

    s3 = boto3.client("s3")
    unchanged = 0
    changed = 0
    unverified = 0

    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue

        if path.name == "pinegrow.json":
            continue

        if path.suffix.lower() not in EXTENSIONS and path.name != "robots.txt":
            continue

        key = path.relative_to(source).as_posix()
        local_md5 = md5_file(path)

        try:
            response = s3.head_object(Bucket=args.bucket, Key=key)
        except ClientError as error:
            status = error.response.get("ResponseMetadata", {}).get(
                "HTTPStatusCode"
            )

            if status == 404:
                print(f"WOULD UPLOAD (new): {key}")
                changed += 1
                continue

            raise

        etag = response["ETag"].strip('"').lower()

        if re.fullmatch(r"[0-9a-f]{32}", etag):
            if local_md5 == etag:
                unchanged += 1
                print(f"SKIP (identical): {key}")
            else:
                changed += 1
                print(f"WOULD UPLOAD (changed): {key}")
        else:
            unverified += 1
            print(f"UNVERIFIED (ETag not MD5): {key}")

    print("\nDeployment preview summary")
    print(f"Unchanged: {unchanged}")
    print(f"Would upload: {changed}")
    print(f"Unverified: {unverified}")
    print("DRY RUN ONLY - no files uploaded or deleted.")


if __name__ == "__main__":
    main()
