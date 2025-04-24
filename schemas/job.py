from pydantic import BaseModel, HttpUrl, field_serializer
from typing import Optional
from datetime import datetime


class Job(BaseModel):
    title: str
    url: HttpUrl
    company: str
    location: Optional[str] = None
    update_time: Optional[datetime] = None
    create_time: Optional[datetime] = None
    job_id: Optional[str] = None
    remote_vs_office: Optional[str] = None

    @field_serializer('url')
    def url2str(self, val) -> str:
        if isinstance(val, HttpUrl):
            return str(val)
        return val

