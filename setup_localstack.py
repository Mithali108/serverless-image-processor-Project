"""Create the local S3 buckets and deploy/configure the thumbnail Lambda."""

import json
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


ENDPOINT_URL = "http://localhost:4566"
REGION = "us-east-1"
INPUT_BUCKET = "input-bucket"
OUTPUT_BUCKET = "output-bucket"
FUNCTION_NAME = "image-thumbnail-processor"
FUNCTION_ROLE = "arn:aws:iam::000000000000:role/lambda-execution-role"
PACKAGE_PATH = Path(__file__).resolve().parent / "build" / "lambda.zip"


def create_bucket_if_missing(s3, name: str) -> None:
    try:
        s3.head_bucket(Bucket=name)
    except ClientError as error:
        status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        code = error.response.get("Error", {}).get("Code")
        if status != 404 and code not in {"404", "NoSuchBucket", "NotFound"}:
            raise
        s3.create_bucket(Bucket=name)
        print(f"Created bucket: {name}")
    else:
        print(f"Bucket already exists: {name}")


def deploy_lambda(lambda_client) -> str:
    if not PACKAGE_PATH.is_file():
        raise FileNotFoundError(
            f"Lambda package not found at {PACKAGE_PATH}. "
            "Run `docker compose run --build --rm lambda-package` first."
        )

    function_config = {
        "FunctionName": FUNCTION_NAME,
        "Runtime": "python3.12",
        "Role": FUNCTION_ROLE,
        "Handler": "lambda_handler.handler",
        "Timeout": 30,
        "MemorySize": 512,
        "Environment": {
            "Variables": {
                "LOCALSTACK_ENDPOINT": "http://localstack:4566",
                "OUTPUT_BUCKET": OUTPUT_BUCKET,
            }
        },
    }
    package = PACKAGE_PATH.read_bytes()
    try:
        try:
            response = lambda_client.get_function(FunctionName=FUNCTION_NAME)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") not in {
                "ResourceNotFoundException",
                "ResourceNotFound",
            }:
                raise
            response = lambda_client.create_function(
                **function_config, Code={"ZipFile": package}
            )
            print(f"Created Lambda: {FUNCTION_NAME}")
        else:
            lambda_client.update_function_code(
                FunctionName=FUNCTION_NAME, ZipFile=package
            )
            lambda_client.update_function_configuration(
                FunctionName=FUNCTION_NAME,
                Runtime=function_config["Runtime"],
                Role=function_config["Role"],
                Handler=function_config["Handler"],
                Timeout=function_config["Timeout"],
                MemorySize=function_config["MemorySize"],
                Environment=function_config["Environment"],
            )
            response = lambda_client.get_function(FunctionName=FUNCTION_NAME)
            print(f"Updated Lambda: {FUNCTION_NAME}")
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") not in {
            "ResourceConflictException",
            "ResourceInUseException",
        }:
            raise
        response = lambda_client.get_function(FunctionName=FUNCTION_NAME)

    function_arn = response.get("FunctionArn") or response.get(
        "Configuration", {}
    ).get("FunctionArn")
    if not function_arn:
        raise ValueError("Lambda deployment response did not include a FunctionArn.")
    return function_arn


def allow_s3_invocation(lambda_client, function_arn: str, bucket_arn: str) -> None:
    try:
        lambda_client.add_permission(
            FunctionName=FUNCTION_NAME,
            StatementId="allow-input-bucket-invocation",
            Action="lambda:InvokeFunction",
            Principal="s3.amazonaws.com",
            SourceArn=bucket_arn,
            SourceAccount="000000000000",
        )
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") != "ResourceConflictException":
            raise

    s3 = boto3.client(
        "s3",
        endpoint_url=ENDPOINT_URL,
        region_name=REGION,
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    current = s3.get_bucket_notification_configuration(Bucket=INPUT_BUCKET)
    configurations = [
        item
        for item in current.get("LambdaFunctionConfigurations", [])
        if item.get("Id") != "image-thumbnail-created"
    ]
    configurations.append(
        {
            "Id": "image-thumbnail-created",
            "LambdaFunctionArn": function_arn,
            "Events": ["s3:ObjectCreated:*"],
        }
    )
    s3.put_bucket_notification_configuration(
        Bucket=INPUT_BUCKET,
        NotificationConfiguration={
            "LambdaFunctionConfigurations": configurations,
            "QueueConfigurations": current.get("QueueConfigurations", []),
            "TopicConfigurations": current.get("TopicConfigurations", []),
            "EventBridgeConfiguration": current.get("EventBridgeConfiguration", {}),
        },
    )
    print(f"Configured S3 upload trigger for: {INPUT_BUCKET}")


def main() -> None:
    s3 = boto3.client(
        "s3",
        endpoint_url=ENDPOINT_URL,
        region_name=REGION,
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    lambda_client = boto3.client(
        "lambda",
        endpoint_url=ENDPOINT_URL,
        region_name=REGION,
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )

    create_bucket_if_missing(s3, INPUT_BUCKET)
    create_bucket_if_missing(s3, OUTPUT_BUCKET)
    function_arn = deploy_lambda(lambda_client)
    allow_s3_invocation(
        lambda_client, function_arn, f"arn:aws:s3:::{INPUT_BUCKET}"
    )
    print(json.dumps({"input_bucket": INPUT_BUCKET, "output_bucket": OUTPUT_BUCKET}))


if __name__ == "__main__":
    main()
