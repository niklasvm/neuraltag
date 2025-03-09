from fastapi import Query
from pydantic import BaseModel


class WebhookGetRequest(BaseModel):
    hub_verify_token: str | None = Query(None, alias="hub.verify_token")
    hub_challenge: str | None = Query(None, alias="hub.challenge")
    hub_mode: str | None = Query(None, alias="hub.mode")
