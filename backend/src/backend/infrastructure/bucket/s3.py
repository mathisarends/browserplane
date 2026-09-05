import asyncio
from pathlib import PurePosixPath
from typing import Any

import boto3
from botocore.exceptions import ClientError

from backend.infrastructure.bucket.credentials import BucketCredentials
from backend.infrastructure.bucket.models import BucketObject
from backend.infrastructure.bucket.port import Bucket
from backend.infrastructure.bucket.settings import BucketSettings

_PART_SIZE = 8 * 1024 * 1024


class S3Bucket(Bucket):
    """Relay async HTTP chunks into an S3 multipart upload."""

    def __init__(
        self, settings: BucketSettings, credentials: BucketCredentials
    ) -> None:
        if settings.name is None:
            raise ValueError("Bucket name is required")
        self._settings = settings
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=settings.endpoint,
            aws_access_key_id=credentials.access_key,
            aws_secret_access_key=credentials.secret_key,
            region_name="us-east-1",
        )
        self._ready = False
        self._lock = asyncio.Lock()

    async def put(self, item: BucketObject) -> None:
        await self._ensure_exists()
        key = str(PurePosixPath(self._settings.prefix.strip("/"), item.key))
        buffer = bytearray()
        upload_id: str | None = None
        parts: list[dict[str, int | str]] = []

        try:
            async for chunk in item.content:
                buffer.extend(chunk)
                while len(buffer) >= _PART_SIZE:
                    if upload_id is None:
                        upload_id = await self._create_upload(key, item.content_type)
                    body = bytes(buffer[:_PART_SIZE])
                    del buffer[:_PART_SIZE]
                    parts.append(await self._upload_part(key, upload_id, body, parts))

            if upload_id is None:
                await asyncio.to_thread(
                    self._client.put_object,
                    Bucket=self._settings.name,
                    Key=key,
                    Body=bytes(buffer),
                    **_content_type(item.content_type),
                )
                return

            if buffer:
                parts.append(
                    await self._upload_part(key, upload_id, bytes(buffer), parts)
                )
            await asyncio.to_thread(
                self._client.complete_multipart_upload,
                Bucket=self._settings.name,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
        except BaseException:
            if upload_id is not None:
                await asyncio.to_thread(
                    self._client.abort_multipart_upload,
                    Bucket=self._settings.name,
                    Key=key,
                    UploadId=upload_id,
                )
            raise

    async def _create_upload(self, key: str, content_type: str | None) -> str:
        response = await asyncio.to_thread(
            self._client.create_multipart_upload,
            Bucket=self._settings.name,
            Key=key,
            **_content_type(content_type),
        )
        return str(response["UploadId"])

    async def _upload_part(
        self,
        key: str,
        upload_id: str,
        body: bytes,
        completed_parts: list[dict[str, int | str]],
    ) -> dict[str, int | str]:
        part_number = len(completed_parts) + 1
        response = await asyncio.to_thread(
            self._client.upload_part,
            Bucket=self._settings.name,
            Key=key,
            UploadId=upload_id,
            PartNumber=part_number,
            Body=body,
        )
        return {"ETag": str(response["ETag"]), "PartNumber": part_number}

    async def _ensure_exists(self) -> None:
        if self._ready:
            return
        async with self._lock:
            if self._ready:
                return
            await asyncio.to_thread(self._ensure_exists_sync)
            self._ready = True

    def _ensure_exists_sync(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._settings.name)
            return
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            if code not in {"404", "NoSuchBucket", "NotFound"}:
                raise
        self._client.create_bucket(Bucket=self._settings.name)


def _content_type(value: str | None) -> dict[str, str]:
    return {"ContentType": value} if value else {}
