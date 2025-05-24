from src.app.config import Settings
from src.database.models import User
from src.tasks.etl.base import ETL
from src.tasks.strava import get_strava_client


class UserETL(ETL):
    def __init__(self, settings: Settings, auth_uuid: int):
        super().__init__(settings=settings)
        self.auth_uuid = auth_uuid

    def extract(self):
        auth = self.db.get_auth(self.auth_uuid)
        client = get_strava_client(
            access_token=auth.access_token,
            refresh_token=auth.refresh_token,
            expires_at=auth.expires_at,
            strava_client_id=self.settings.strava_client_id,
            strava_client_secret=self.settings.strava_client_secret,
        )
        self._athlete = client.get_athlete()

    def load(self):
        user = User(
            athlete_id=self._athlete.id,
            auth_uuid=self.auth_uuid,
            name=self._athlete.firstname,
            lastname=self._athlete.lastname,
            sex=self._athlete.sex,
            profile=self._athlete.profile,
            profile_medium=self._athlete.profile_medium,
            city=self._athlete.city,
            state=self._athlete.state,
            country=self._athlete.country,
        )

        self.db.add_user(user)
        return user
