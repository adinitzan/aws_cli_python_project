from time import sleep
import boto3
import botocore.exceptions
from botocore.exceptions import ClientError
import time
import json
from posixpath import split

# AWS Clients
s3 = boto3.client('s3')
ec2 = boto3.resource('ec2')
ec2_client = boto3.client('ec2')
route53 = boto3.client('route53')

# Helper function for getting a specific tag value from a resource
def get_tag_value(resource, key):
    if resource.tags:
        for tag in resource.tags:
            if tag['Key'] == key:
                return tag['Value']
    return None

# Lists all instances filtered by specific tags
def list_instances(bool_id=False, instance_id="", get_instances_var=False):
    instances = list(ec2.instances.filter(
        Filters=[
            {'Name': 'tag:Owner', 'Values': ['adibeker']},
            {'Name': 'tag:MadeWithCli', 'Values': ['yes']},
            {'Name': 'instance-state-name', 'Values': ['running', 'stopped', 'Stopping']}
        ]
    ))
    if get_instances_var:
        return instances
    
    for instance in instances:
        name_tag = get_tag_value(instance, 'Name') or ""
        if bool_id:
            if instance.id == instance_id:
                print(f"ID: {instance.id}\nName: {name_tag}\nType: {instance.instance_type}\nState: {instance.state['Name']}")
                print("*" * 50)
        else:
            print(f"ID: {instance.id}\nName: {name_tag}\nType: {instance.instance_type}\nState: {instance.state['Name']}")
            print("*" * 50)

def get_next_instance_name():
    # Get all running and stopped instances
    instances = ec2_client.describe_instances(
        Filters=[
            {'Name': 'tag:Owner', 'Values': ['adibeker']},
            {'Name': 'tag:MadeWithCli', 'Values': ['yes']},
            {'Name': 'tag:Name', 'Values': ['adibeker_*']}
        ]
    )
    
    existing_names = []
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            for tag in instance.get('Tags', []):
                if tag['Key'] == 'Name' and tag['Value'].startswith('adibeker_'):
                    existing_names.append(tag['Value'])
    
    # Find the next number
    next_number = 1
    while f"adibeker_{next_number}" in existing_names:
        next_number += 1
    
    return f"adibeker_{next_number}"

# Create new EC2 instances
def create_instances():

    num_created_instances = 0
    ami_choice = ""
    instance_type = ""
    finished_creating_instance = False

    instances = ec2.instances.filter(
        Filters=[{'Name': 'tag:Owner', 'Values': ['adibeker']},
                 {'Name': 'tag:MadeWithCli', 'Values': ['yes']}]
    )
    for instance in instances:
        num_created_instances += 1

    if num_created_instances >= 2:
        print("Error: You can only have a maximum of 2 instances.")
        return
    
    while not finished_creating_instance:
        ami_choice = input("please choose AMI:\nAmazon Linux\nUbuntu\n").lower()
        instance_type = input("please choose instance type:\nt3.nano\nt4g.nano\n").lower()

        # AMI selection
        ami_dict = {
            "amazon linux": {"t3.nano": "ami-053a45fff0a704a47", "t4g.nano": "ami-0c518311db5640eff"},
            "ubuntu": {"t3.nano": "ami-04b4f1a9cf54c11d0", "t4g.nano": "ami-0a7a4e87939439934"}
        }

        if ami_choice in ami_dict and instance_type in ami_dict[ami_choice]:
            ami_choice = ami_dict[ami_choice][instance_type]
            finished_creating_instance = True
        else:
            print("Invalid selection, please start over.")

    new_instance_name = get_next_instance_name()
    
    ec2.create_instances(
        MinCount=1,
        MaxCount=1,
        ImageId=ami_choice,
        InstanceType=instance_type,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [
                {'Key': 'Owner', 'Value': 'adibeker'},
                {'Key': 'MadeWithCli', 'Value': 'yes'},
                {'Key': 'Name', 'Value': new_instance_name }
            ]
        }]
    )

# Stop, start, or delete EC2 instances
def stop_start_delete_instances(instance_id, instance_state):
    try:
        action_ssd = {
            "stop": ec2.meta.client.stop_instances,
            "start": ec2.meta.client.start_instances,
            "delete": ec2.meta.client.terminate_instances
        }

        if instance_state not in action_ssd:
            print("Invalid action.")
            return

        if instance_state in action_ssd:
            action_ssd[instance_state](InstanceIds=[instance_id])
            time.sleep(30)
            list_instances(True, instance_id)
        
    except botocore.exceptions.ClientError as e:
        error_message = str(e)
        if "is not in a valid state" in error_message:
            print(f"Error: Instance {instance_id} is not in a valid state to be {instance_state}ed. Try again later.")
        else:
            print(f"Unexpected error: {error_message}")

# Instance management options (List, Create, Stop/Start/Delete)
def instances_management():
    instances = list_instances(False, "", True)
    while True:
        instance_choice = input("please choose an option:\n1. List all\n2. Create instance\n3. Stop/Start/Delete instance\n")
        
        if instance_choice == "1":
            list_instances()
        
        elif instance_choice == "2" and len(instances) < 2:
            create_instances()
        
        elif instance_choice == "2":
            print("You already have more than 2 instances, can't create more.")
        
        elif instance_choice == "3":
            list_instances()
            while True:
                instance_id = input("please choose instance ID or type 'exit' to return:\n")
               
                if any(instance.id == instance_id for instance in instances):
                    break
                elif instance_id == "exit":
                    return
                else:
                    print("Invalid ID, try again.")
            while True:
                instance_state = input("Stop/start/delete the instance:\nOr type 'exit' to return\n").lower()
                if instance_state in ["stop", "start", "delete"]:
                    stop_start_delete_instances(instance_id, instance_state)
                    return
                elif instance_state == "exit":
                    return
                else:
                    print("Please write 'start', 'stop', or 'delete'.")
        else:
            print("Invalid choice, try again.")

def get_bucket_with_tag(tag_key='Owner', tag_value='adibeker'):
    response = s3.list_buckets()
    buckets = response['Buckets']
    buckets_with_tag = []

    for bucket in buckets:
        bucket_name = bucket['Name']
        try:
            tags_response = s3.get_bucket_tagging(Bucket=bucket_name)
            for tag in tags_response.get('TagSet', []):
                if tag['Key'] == tag_key and tag['Value'] == tag_value:
                    buckets_with_tag.append(bucket_name)
                    break
        except ClientError:
            continue
    return buckets_with_tag


# List all S3 buckets with specific tags
def s3_list(get_bucket_list=False, take_bucket_name=False):
    buckets_with_tag = get_bucket_with_tag()
    
    if get_bucket_list:
        return buckets_with_tag
    elif take_bucket_name:
        return buckets_with_tag[0] if buckets_with_tag else None
    else:
        print(buckets_with_tag[0] if buckets_with_tag else "No buckets found.")
        print("*" * 50)

# Upload a file to an S3 bucket
def s3_upload():
    try:
        bucket_name = s3_list(False, True)
        if not bucket_name:
            print("No buckets available.")
            return
        choise_file_location = input("please choose the exact file location you want to add:\n")
        key_name = input("please choose the path where the file will be stored:\n")
        s3.upload_file(choise_file_location, bucket_name, key_name)
    except FileNotFoundError:
        print("File not found, try again.")

# Create a new S3 bucket
def s3_create():
    if len(get_bucket_with_tag()) >= 2:
        print("Too many buckets. Try again later.")
    else:
        bucket_name = input("please choose your bucket's name:\n")
        try:
            s3.create_bucket(Bucket=bucket_name)
            print(f"Bucket {bucket_name} created successfully.")

        except botocore.exceptions.ParamValidationError:
            print("Invalid bucket name. Try again.")
            return
        except botocore.exceptions.ClientError:
            print("Error creating bucket. Try again.")
            return

        if input("Do you want the bucket to be public? yes/no\n").lower() == "yes":
            if input("are you sure that you want the bucket be public? yes/no\n").lower() == "yes":
                s3.put_public_access_block(
                    Bucket=bucket_name,
                    PublicAccessBlockConfiguration={
                        'BlockPublicAcls': False,
                        'IgnorePublicAcls': False,
                        'BlockPublicPolicy': False,
                        'RestrictPublicBuckets': False
                    }
                )
                public_policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "PublicReadGetObject",
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": "s3:GetObject",
                            "Resource": f"arn:aws:s3:::{bucket_name}/*"
                        }
                    ]
                }
                s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(public_policy))
                print("Bucket made public.")
        else:
            print("Bucket made private.")

        s3.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={
                'TagSet': [
                    {'Key': 'Owner', 'Value': 'adibeker'},
                    {'Key': 'MadeWithCli', 'Value': 'yes'}
                ]
            },
        )

# Choose actions for S3
def s3_management():
    while True:
        s3_choice = input("please choose an action:\n1. List all\n2. Create S3\n3. Upload file\n")
        if s3_choice == "1":
            s3_list()
        elif s3_choice == "2":
            s3_create()
        elif s3_choice == "3":
            s3_upload()
        else:
            print("Invalid choice, try again.")

def list_zones_route53(get_list_of_my_zones=False, get_names=False):
    routes = route53.list_hosted_zones()

    list_of_zones_id = [route['Id'].split("/")[-1] for route in routes['HostedZones']]
    
    list_of_my_zones = []
    for zone_id in list_of_zones_id:
        response = route53.list_tags_for_resource(
            ResourceType='hostedzone',
            ResourceId=zone_id
        )
        try:
            if response['ResourceTagSet']['Tags'][0]['Value'] == 'yes' and response['ResourceTagSet']['Tags'][1]['Value'] == 'adibeker':
                list_of_my_zones.append(zone_id)
        except IndexError:
            continue

    if get_list_of_my_zones:
        return list_of_my_zones
    if get_names:
        if list_of_my_zones:
            name_check = route53.get_hosted_zone(Id=list_of_my_zones[0])
            return name_check['HostedZone']['Name']
        return None

def manage_dnf_records():
    zone_name = list_zones_route53(False, True)
    zone_id = list_zones_route53(True, False)[0]
    
    choise_action = input("please choose create/delete/upsert:\n").lower()
    if choise_action == "create":
        choise_name = input("please choose the name for the record:\n")
        choise_ip = input("please choose the IP for the record:\n")
        
        response = route53.change_resource_record_sets(
            ChangeBatch={
                'Changes': [
                    {
                        'Action': choise_action.upper(),
                        'ResourceRecordSet': {
                            'Name': f"{choise_name}.{zone_name}",
                            'ResourceRecords': [
                                {
                                    'Value': choise_ip,
                                },
                            ],
                            'TTL': 100,
                            'Type': 'A',
                        },
                    },
                ],
            },
            HostedZoneId=zone_id,
        )
        print(f"Record created: {choise_name}.{zone_name} -> {choise_ip}")
    elif choise_action in ["delete", "upsert"]:
        list_record = route53.list_resource_record_sets(HostedZoneId=zone_id)
        
        for i, record in enumerate(list_record['ResourceRecordSets'], 1):
            print(f"{i}) {record['Name']} -> {record['ResourceRecords'][0]['Value']}")
        
        choise_record = int(input("please choose a record number to modify:\n"))
        choise_record -= 1  # Adjust for zero-based indexing
        
        if choise_action == "delete":
            response_delete = route53.change_resource_record_sets(
                ChangeBatch={
                    'Changes': [
                        {
                            'Action': choise_action.upper(),
                            'ResourceRecordSet': {
                                'Name': list_record['ResourceRecordSets'][choise_record]['Name'],
                                'ResourceRecords': [
                                    {
                                        'Value': list_record['ResourceRecordSets'][choise_record]['ResourceRecords'][0]['Value'],
                                    },
                                ],
                                'TTL': 100,
                                'Type': 'A',
                            },
                        },
                    ],
                },
                HostedZoneId=zone_id,
            )
            print(f"Deleted record: {list_record['ResourceRecordSets'][choise_record]['Name']}")
        else:
            changed_ip = input("Enter the new IP:\n")
            response_change = route53.change_resource_record_sets(
                ChangeBatch={
                    'Changes': [
                        {
                            'Action': choise_action.upper(),
                            'ResourceRecordSet': {
                                'Name': list_record['ResourceRecordSets'][choise_record]['Name'],
                                'ResourceRecords': [
                                    {
                                        'Value': changed_ip,
                                    },
                                ],
                                'TTL': 100,
                                'Type': 'A',
                            },
                        },
                    ],
                },
                HostedZoneId=zone_id,
            )
            print(f"Updated record: {list_record['ResourceRecordSets'][choise_record]['Name']} -> {changed_ip}")

def extract_route53_id(hosted_zone_id):
    "Helper function to extract the Route 53 ID from the full hosted zone ID."
    return hosted_zone_id.split('/')[-1]

def validate_zone_name(zone_name):
    "Validate the domain name according to AWS Route 53 domain naming rules."
    if len(zone_name) < 1 or len(zone_name) > 255:
        return False
    if not zone_name[-1] == '.':
        zone_name += '.'
    return True

def create_zone_route53():
    if len(list_zones_route53(True)) >= 2:
        print("You already have enough zones.")
        return

    while True:
        route53_name = input("Please choose the name.com for your zone:\n")
        
        # Validate the name before proceeding
        if not validate_zone_name(route53_name):
            print("Invalid domain name format. Please try again.")
            continue

        try:
            response = route53.create_hosted_zone(
                Name=route53_name,
                CallerReference=f"{route53_name}-{int(time.time())}"
            )
            route53_hostzone_id = response['HostedZone']['Id']
            route53_id = extract_route53_id(route53_hostzone_id)
            
            # Tag the new hosted zone
            route53.change_tags_for_resource(
                ResourceId=route53_id,
                ResourceType='hostedzone',
                AddTags=[
                    {'Key': 'Owner', 'Value': 'adibeker'},
                    {'Key': 'MadeWithCli', 'Value': 'yes'}
                ]
            )

            print(f"Created new zone: {response['HostedZone']['Name']}")
            break  # Break the loop after successful creation
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'InvalidDomainName':
                print("Invalid zone name.")
            else:
                print(f"Error occurred: {e.response['Error']['Message']}. Try again with a different name.")
            break  # Exit the loop after handling error

# Manage Route53 zones and records
def route53_management():
    while True:
        route53_choice = input("please choose an action:\n1. Create Zone\n2. Manage DNS Records\n")
        if route53_choice == "1":
            create_zone_route53()
        elif route53_choice == "2":
            manage_dnf_records()
        else:
            print("Invalid choice, try again.")

# Main program loop
while True:
    num_action = input("please choose a service to work on:\n1. Instances\n2. S3\n3. Route53\n4. Exit\n")
    if num_action == "1":
        instances_management()
    elif num_action == "2":
        s3_management()
    elif num_action == "3":
        route53_management()
    elif num_action == "4":
        break
    else:
        print("Invalid choice.")
