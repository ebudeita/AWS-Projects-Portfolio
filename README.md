Static Website Hosting on AWS (S3 + CloudFront + Route 53)

This project demonstrates how to host a secure, scalable static website using Amazon Web Services. The website is hosted on Amazon S3, delivered globally through CloudFront, and managed with a custom domain using Route 53.

This project was built as part of my AWS Solutions Architect learning journey and showcases my ability to design and implement a cost-effective and highly available cloud architecture.

Architecture
The architecture uses a serverless and highly available design:
- Amazon S3 – Stores and hosts static website files
- Amazon CloudFront – Provides global content delivery and caching
- Amazon Route 53 – Manages DNS and domain routing
- HTTPS – Secured using SSL/TLS
- IAM – Used for secure access control
Users access the website through CloudFront, which retrieves content securely from the S3 bucket.

Features
Static website hosting
Global content delivery with low latency
Secure HTTPS access
Custom domain configuration
Cost-optimized architecture
Scalable serverless design

Project Objectives
The goal of this project was to:
- Host a static website on AWS
- Configure secure access to S3
- Implement CloudFront for performance
- Connect a custom domain using Route 53
- Follow AWS architecture best practices
- Build a real-world cloud project for my portfolio

Deployment Steps
1. Create S3 Bucket
Created an S3 bucket
Enabled static website hosting
Uploaded website files
Configured permissions

2. Configure CloudFront
Created CloudFront distribution
Connected S3 as origin
Enabled HTTPS
Configured caching

3. Configure Route 53
Registered my domain
Created hosted zone
Added DNS records
Connected domain to CloudFront

4. Secure Access
Restricted direct S3 access
Allowed access only through CloudFront
Configured IAM permissions

Technologies Used
AWS S3
AWS CloudFront
AWS Route 53
IAM
HTML
CSS
GitHub

Lessons Learned
How S3 static website hosting works
How CloudFront improves performance
DNS configuration with Route 53
Securing S3 with CloudFront
AWS architecture fundamentals
Troubleshooting deployment issues

Project Status
Completed and live.

This project is part of my AWS cloud portfolio as I work toward cloud engineering and solutions architecture roles.

Future Improvements
Add CI/CD pipeline
Automate deployment
Add monitoring with CloudWatch
Improve caching strategy
Add infrastructure as code

Author
Ita Ebude
AWS Certified Solutions Architect – Associate
Cloud Portfolio: https://itaebude.com/
LinkedIn: https://www.linkedin.com/in/ebude-ita/

