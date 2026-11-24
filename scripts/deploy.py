#!/usr/bin/env python3
"""Checksum-based deployment to Amazon S3."""

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

CONTENT_TYPES = {
    ".html":  "text/html; charset=utf-8",
    ".css":   "text/css; charset=utf-8",
    ".js":    "application/javascript; charset=utf-8",
    ".json":  "application/json; charset=utf-8",
    ".xml":   "application/xml; charset=utf-8",
    ".ico":   "image/x-icon",
    ".png":   "image/png",
    ".jpg":   "image/jpeg",
    ".jpeg":  "image/jpeg",
    ".gif":   "image/gif",
    ".svg":   "image/svg+xml",
    ".webp":  "image/webp",
    ".woff":  "font/woff",
    ".woff2": "font/woff2",
    ".ttf":   "font/ttf",
}

CACHE_CONTROL = {
    ".html": "no-cache",
}

DEFAULT_CACHE_CONTROL = "public, max-age=31536000, immutable"


def md5_file(path):
    digest = hashlib.md5(usedforsecurity=False)

    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def content_type_for(path):
    if path.name == "robots.txt":
        return "text/plain; charset=utf-8"
    return CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")


def cache_control_for(path):
    return CACHE_CONTROL.get(path.suffix.lower(), DEFAULT_CACHE_CONTROL)


def upload_file(s3, bucket, key, path):
    body = path.read_bytes()
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType=content_type_for(path),
        CacheControl=cache_control_for(path),
    )


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
                upload_file(s3, args.bucket, key, path)
                print(f"UPLOADED (new): {key}")
                changed += 1
                continue

            raise

        etag = response["ETag"].strip('"').lower()

        if re.fullmatch(r"[0-9a-f]{32}", etag):
            if local_md5 == etag:
                unchanged += 1
                print(f"SKIP (identical): {key}")
            else:
                upload_file(s3, args.bucket, key, path)
                changed += 1
                print(f"UPLOADED (changed): {key}")
        else:
            upload_file(s3, args.bucket, key, path)
            unverified += 1
            print(f"UNVERIFIED UPLOADED: {key}")

    print("\nDeployment summary")
    print(f"Unchanged: {unchanged}")
    print(f"Uploaded:  {changed}")
    print(f"Unverified uploaded: {unverified}")
    print("Deployment complete.")

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as fh:
            value = "true" if (changed + unverified) > 0 else "false"
            fh.write(f"changed={value}\n")


if __name__ == "__main__":
    main()
