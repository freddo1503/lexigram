import re

from pydantic import BaseModel, field_validator

from app.config import settings

_UUID_SUFFIX = re.compile(
    r"/images/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.jpg$"
)


class ImagePayload(BaseModel):
    image_url: str
    image_description: str

    @field_validator("image_url")
    @classmethod
    def validate_s3_url(cls, v: str) -> str:
        expected_prefix = (
            f"https://{settings.s3_bucket_name}.s3."
            f"{settings.aws_region}.amazonaws.com/images/"
        )
        if not v.startswith(expected_prefix) or not _UUID_SUFFIX.search(v):
            raise ValueError(
                f"image_url must start with {expected_prefix} and end with "
                "/<uuid>.jpg. Use the 'Mistral Image Tool' to generate the image."
            )
        return v
