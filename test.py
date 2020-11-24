import boto3
from dotenv import load_dotenv
import os
from botocore.exceptions import ClientError
import time
elbclient = boto3.client('elb', region_name='us-east-1')
print(elbclient.waiter_names)