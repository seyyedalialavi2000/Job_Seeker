from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime


class Job(BaseModel):
    title: str
    url: HttpUrl
    location: Optional[str] = None
    update_time: Optional[datetime] = None
    create_time: Optional[datetime] = None
    job_id: Optional[str] = None
    remote_vs_office: Optional[str] = None

