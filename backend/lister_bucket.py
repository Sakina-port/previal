import os
import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv()

client = boto3.client(
    "s3",
    endpoint_url=os.getenv("S3_ENDPOINT_URL"),
    aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
    region_name=os.getenv("S3_REGION", "us-east-1"),
    config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
)

reponse = client.list_objects_v2(Bucket=os.getenv("S3_BUCKET"))
objets = reponse.get("Contents", [])
print(f"{len(objets)} fichier(s) dans le bucket :")
for objet in objets:
    print(" -", objet["Key"], objet["Size"], "octets")