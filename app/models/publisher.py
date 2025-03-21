from pydantic import BaseModel, HttpUrl, constr, field_validator


class MediaPayload(BaseModel):
    image_url: HttpUrl
    caption: constr(min_length=1)

    @field_validator("image_url")
    def validate_image_url(cls, value: HttpUrl) -> HttpUrl:
        if not value.path.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
            raise ValueError(
                "The URL must point to a valid image file (jpg, jpeg, png, gif, webp)."
            )
        return value


class MediaCreationResponse(BaseModel):
    id: str


class StatusResponse(BaseModel):
    status_code: str


class PublishResponse(BaseModel):
    id: str
