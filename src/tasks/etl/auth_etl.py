import uuid

from stravalib import Client

from src.app.config import Settings
from src.database.models import Auth
from src.tasks.etl.base import ETL


class AuthETL(ETL):
    def __init__(self, code: str, scope: str, settings: Settings):
        super().__init__(settings=settings)
        self.code = code
        self.scope = scope

    def extract(self):
        client = Client()
        self._token_response = client.exchange_code_for_token(
            client_id=self.settings.strava_client_id,
            client_secret=self.settings.strava_client_secret,
            code=self.code,
        )

    def load(self):
        auth = Auth(
            uuid=uuid.uuid4(),
            access_token=self._token_response["access_token"],
            refresh_token=self._token_response["refresh_token"],
            expires_at=self._token_response["expires_at"],
            scope=self.scope,
        )
        self.db.add_auth(auth)
        return auth.uuid
