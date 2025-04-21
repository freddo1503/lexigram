from pydantic import BaseModel


class ImagePayload(BaseModel):
    image_url: str
    image_description: str
