from src.app.config import Settings
from src.tasks.data import summary_activity_to_activity_model
from src.tasks.etl.base import ETL
from src.tasks.strava import get_strava_client


class SingleActivityETL(ETL):
    def __init__(self, settings: Settings, activity_id: int, athlete_id: int):
        super().__init__(settings=settings)
        self.activity_id = activity_id
        self.athlete_id = athlete_id

    def extract(self):
        auth = self.db.get_auth_by_athlete_id(self.athlete_id)

        client = get_strava_client(
            access_token=auth.access_token,
            refresh_token=auth.refresh_token,
            expires_at=auth.expires_at,
            strava_client_id=self.settings.strava_client_id,
            strava_client_secret=self.settings.strava_client_secret,
        )
        self._activity = client.get_activity(self.activity_id)

    def transform(self):
        self._activity_model = summary_activity_to_activity_model(self._activity)

    def load(self):
        self.db.add_activity(self._activity_model)
        return self._activity_model
