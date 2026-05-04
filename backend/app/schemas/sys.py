from pydantic import BaseModel
from typing import Any

class ConfigUpdateRequest(BaseModel):
    config_key: str
    config_value: Any