from typing import IO

import boto3
from botocore.client import Config as BotoConfig
from mypy_boto3_s3.client import S3Client

from app.core.config import settings

_client: S3Client | None = None
_presign_client: S3Client | None = None


def _build_client(endpoint_url: str) -> S3Client:
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        region_name=settings.S3_REGION,
        config=BotoConfig(s3={"addressing_style": "path"}),
    )


def _get_client() -> S3Client:
    global _client
    if _client is None:
        _client = _build_client(settings.S3_ENDPOINT_URL)
    return _client


def _get_presign_client() -> S3Client:
    global _presign_client
    if _presign_client is None:
        _presign_client = _build_client(settings.s3_public_endpoint_url)
    return _presign_client


def upload_document(storage_key: str, fileobj: IO[bytes], content_type: str | None = None) -> None:
    extra_args = {"ContentType": content_type} if content_type else {}
    _get_client().upload_fileobj(fileobj, settings.S3_BUCKET, storage_key, ExtraArgs=extra_args)


def download_document_bytes(storage_key: str) -> bytes:
    response = _get_client().get_object(Bucket=settings.S3_BUCKET, Key=storage_key)
    return response["Body"].read()


def delete_document(storage_key: str) -> None:
    _get_client().delete_object(Bucket=settings.S3_BUCKET, Key=storage_key)


def generate_presigned_download_url(storage_key: str, filename: str, expires_in: int = 300) -> str:
    return _get_presign_client().generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.S3_BUCKET,
            "Key": storage_key,
            "ResponseContentDisposition": f'attachment; filename="{filename}"',
        },
        ExpiresIn=expires_in,
    )