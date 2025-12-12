import boto3
import ray
from botocore.config import Config

session = boto3.Session(profile_name='default')  # or another profile
s3 = session.client('s3')    

session = boto3.Session(profile_name='default')
s3 = session.client(
    's3', config=Config(s3={'addressing_style': 'virtual'}))
print("Access Key:", session.get_credentials().access_key)

for bucket in s3.list_buckets()['Buckets']:
    print("Bucket:", bucket['Name'])
    print("Access Key:", session.get_credentials().access_key)
