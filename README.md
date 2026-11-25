# AWS Portfolio Website with Automated Deployment

A live portfolio hosted on Amazon S3, delivered through CloudFront, and connected to a custom domain through Route 53. GitHub Actions automates website deployment using AWS OIDC authentication and a Python deployment script.

**Live website:** [itaebude.com](https://itaebude.com/)  
**Project case study:** [Website hosting and deployment](https://itaebude.com/project1.html)

## Project Overview

I initially deployed this website manually to learn AWS hosting, DNS, HTTPS, and access control. I then added an automated deployment workflow so website updates committed to `main` can be published without manually uploading files to S3.

The project demonstrates AWS hosting, identity federation, Python automation, content comparison, and troubleshooting across the browser, deployment pipeline, and AWS services.

## Architecture

| Component | Purpose |
|---|---|
| Amazon S3 | Stores website HTML, CSS, JavaScript, and assets |
| Amazon CloudFront | Delivers and caches website content |
| Amazon Route 53 | Routes the custom domain to CloudFront |
| AWS Certificate Manager | Provides the certificate for HTTPS |
| GitHub Actions | Runs website validation and automated deployment |
| IAM and OIDC | Allow the workflow to assume an AWS role using temporary credentials |
| Python and Boto3 | Compare local files with S3 objects and upload changes |

Visitors access the website through CloudFront. Deployment is a separate flow: GitHub Actions assumes an AWS role, publishes files to S3, and requests a CloudFront invalidation when uploads occur.

## Automated Deployment

The workflow is defined in [deploy.yml](.github/workflows/deploy.yml), with upload logic in [scripts/deploy.py](scripts/deploy.py).

1. **Trigger:** A push to `main` affecting configured website file types or the workflow file starts deployment. The workflow can also be started manually.
2. **Prepare the runner:** GitHub Actions checks out the repository, configures Python 3.12, and installs Boto3.
3. **Authenticate:** GitHub OIDC allows the runner to assume the configured IAM role without storing long-lived AWS access keys in GitHub.
4. **Prepare and validate files:** The workflow copies tracked files matching its deployment extensions into a staging directory. It stops if `index.html`, `portfolio.html`, or `style.css` is missing or empty.
5. **Generate a manifest:** The workflow generates a SHA-256 checksum manifest on the runner. This manifest is separate from the S3 comparison performed by the upload script.
6. **Compare and upload:** The Python script compares each local file's MD5 checksum with the S3 object's ETag when it has a single-part MD5 format. It skips identical content and uploads new or changed content. Objects with other ETag formats are uploaded conservatively.
7. **Refresh the CDN:** If any files were uploaded, the workflow requests a CloudFront invalidation for `/*`. When no uploads occur, it skips invalidation.

Uploads include content-type and cache-control headers. HTML uses `no-cache`; other supported assets currently use a one-year immutable cache policy.

## Repository Configuration

The workflow uses:

| Setting | GitHub configuration |
|---|---|
| AWS role ARN | Secret: `AWS_ROLE_ARN` |
| AWS Region | Variable: `AWS_REGION` |
| Website bucket | Variable: `S3_BUCKET` |
| CloudFront distribution | Variable: `CLOUDFRONT_DISTRIBUTION_ID` |

The AWS role must trust the intended GitHub repository and branch through OIDC and permit the S3 and CloudFront operations required by the workflow.

## Serverless Contact Form

The website also includes a contact form that submits JSON to API Gateway. A Node.js Lambda function uses Amazon SES to send the enquiry by email, with the visitor's address used for Reply-To.

The form was tested locally and on the live website. Received messages contained the submitted name, email, subject, and message, and replies targeted the visitor's email.

The website deployment workflow publishes frontend files. It does not deploy the Lambda function or provision API Gateway and SES.

## Validation and Results

- GitHub Actions completed successfully after changes were pushed to `main`.
- Deployment logs showed new files uploaded and identical files skipped.
- The updated contact form worked on the live domain and delivered a test email.
- Email content and Reply-To were checked manually.

The pipeline currently performs file-presence checks, not a full automated application test suite. A successful workflow run is followed by live-site verification.

## Lessons Learned

- How S3, CloudFront, Route 53, and ACM work together to deliver a website.
- How GitHub OIDC supports temporary AWS credentials for deployment.
- How content comparison avoids uploading unchanged files.
- Why checksum generation and the actual upload comparison must be documented separately.
- How to connect upload results to conditional CloudFront invalidation.
- How to troubleshoot frontend initialization and verify email delivery end to end.
- Why local testing and live-domain testing are both necessary.

## Current Limitations and Next Improvements

- Add automated HTML, JavaScript, and link checks before deployment.
- Use versioned or content-hashed asset filenames before relying on long-lived immutable browser caching.
- Restrict deployment staging to public website directories; the current extension-based selection can include backend JavaScript and package JSON files.
- Add the deployment Python script to the workflow's push path filters so script-only changes trigger deployment.
- Add explicit handling for removed website files; the current script does not delete stale S3 objects.
- Include metadata changes in comparison; identical content currently skips header updates.
- Complete SES domain authentication to address the Gmail sender warning.
- Define infrastructure as code and improve monitoring and rollback procedures.

## Technologies

Amazon S3 · CloudFront · Route 53 · ACM · IAM · OIDC · GitHub Actions · Python · Boto3 · HTML · CSS · JavaScript · API Gateway · AWS Lambda · Amazon SES

## Author

**Ita Ebude**  
AWS Certified Solutions Architect – Associate

[Portfolio](https://itaebude.com/) · [LinkedIn](https://www.linkedin.com/in/ebude-ita/)

