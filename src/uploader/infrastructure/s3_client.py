"""SeaweedFS S3-compatible object storage adapter backed by aiobotocore."""

from pathlib import Path
from typing import Any

from aiobotocore.session import get_session
from botocore.exceptions import ClientError

from uploader.specs.constants import (
    S3_ALREADY_EXISTS_ERROR_CODES,
    S3_ETAG_RESPONSE_KEY,
    S3_REGION_NAME,
    S3_SERVICE_NAME,
)


class S3ObjectStorage:
    """Uploads files using a shared async S3 client."""

    def __init__(
        self, *, endpoint_url: str, bucket: str, access_key_id: str, secret_access_key: str
    ) -> None:
        self._endpoint_url = endpoint_url
        self._bucket = bucket
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._client_context: Any | None = None
        self._client: Any | None = None

    async def __aenter__(self) -> S3ObjectStorage:
        client_context: Any = get_session().create_client(
            S3_SERVICE_NAME,
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key_id,
            aws_secret_access_key=self._secret_access_key,
            region_name=S3_REGION_NAME,
        )
        self._client_context = client_context
        client = await client_context.__aenter__()
        self._client = client
        try:
            await client.create_bucket(Bucket=self._bucket)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") not in S3_ALREADY_EXISTS_ERROR_CODES:
                raise
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client_context is not None:
            await self._client_context.__aexit__(*args)

    async def upload_file(
        self, *, key: str, path: Path, content_type: str, cache_control: str
    ) -> str:
        if self._client is None:
            raise RuntimeError("S3ObjectStorage must be used as an async context manager")
        with path.open("rb") as source:
            response = await self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=source,
                ContentType=content_type,
                CacheControl=cache_control,
            )
        return str(response[S3_ETAG_RESPONSE_KEY])
