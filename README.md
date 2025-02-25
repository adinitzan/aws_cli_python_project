# AWS CLI Automation Script

This script automates the management of AWS EC2 instances, S3 buckets, and Route 53 hosted zones and records. It allows you to perform several common tasks related to these AWS services through a simple command-line interface.

## Requirements

1. **AWS Account**: You need an AWS account and credentials to use this script.
2. **AWS CLI**: Ensure that AWS CLI is installed and configured with your credentials.
3. **Python 3.X**: The script requires Python 3 and the `boto3` package for interacting with AWS services.

## Install Dependencies
   You can install it using pip:
   pip install boto3

## How to Use

1. Clone this repository or copy the script.
2. Run the script:
python aws_cli_automation.py

choose a service to work on:
1. Instances
2. S3
3. Route53
4. Exit

### EC2 Instance Management

- **List Instances**: Displays EC2 instances filtered by tags.
- **Create Instance**: Creates a new EC2 instance with a user-defined AMI and instance type.
- **Stop, Start, Delete Instances**: Allows you to stop, start, or terminate existing EC2 instances.

### S3 Bucket Management

- **List Buckets**: Lists all S3 buckets with a specific tag (`Owner: adibeker`).
- **Create Bucket**: Creates a new S3 bucket and allows you to choose whether the bucket should be public or private.
- **Upload File**: Uploads a file to a specific S3 bucket.

### Route 53 Zone and Record Management

- **Create Zone**: Creates a new hosted zone in Route 53.
- **Manage DNS Records**: Allows you to create, delete, or modify DNS records within a hosted zone.
