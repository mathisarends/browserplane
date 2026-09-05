import asyncio
from pathlib import PurePosixPath
from typing import Any

import boto3
from botocore.exceptions import ClientError

from data_plane.infrastructure.bucket.credentials import BucketCredentials
from data_plane.infrastructure.bucket.models import BucketObject
from data_plane.infrastructure.bucket.port import Bucket
from data_plane.infrastructure.bucket.settings import BucketSettings


class S3Bucket(Bucket):
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
        extra_args = {"ContentType": item.content_type} if item.content_type else None
        kwargs = {"ExtraArgs": extra_args} if extra_args else {}
        await asyncio.to_thread(
            self._client.upload_file,
            str(item.path),
            self._settings.name,
            key,
            **kwargs,
        )

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
