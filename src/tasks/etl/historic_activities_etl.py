import datetime


from src.app.config import Settings
from src.database.models import Activity
from src.tasks.data import summary_activity_to_activity_model
from src.tasks.etl.base import ETL
from src.tasks.strava import get_strava_client


class ActivitiesETL(ETL):
    def __init__(
        self,
        settings: Settings,
        auth_uuid: int,
        before: datetime.datetime,
        after: datetime.datetime,
    ):
        super().__init__(settings=settings)
        self.auth_uuid = auth_uuid
        self.before = before
        self.after = after

    def extract(self):
        auth = self.db.get_auth(self.auth_uuid)
        client = get_strava_client(
            access_token=auth.access_token,
            refresh_token=auth.refresh_token,
            expires_at=auth.expires_at,
            strava_client_id=self.settings.strava_client_id,
            strava_client_secret=self.settings.strava_client_secret,
        )
        self._summary_activities = client.get_activities(
            after=self.after, before=self.before
        )
        self._summary_activities = [x for x in self._summary_activities]

    def transform(self):
        self._activities: list[Activity] = []
        for summary_activity in self._summary_activities:
            activity = summary_activity_to_activity_model(summary_activity)
            self._activities.append(activity)

    def load(self):
        self.db.add_activities_bulk(self._activities)
