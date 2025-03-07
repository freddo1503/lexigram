import pydantic


class Post(pydantic.BaseModel):
    title: str


class Image(Post):
    image_url: str


class Text(Post):
    text: str
