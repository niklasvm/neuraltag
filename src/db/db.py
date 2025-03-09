import datetime
import logging
from typing import Optional
from sqlalchemy import create_engine
from src.db.models import Activity, Auth, Base
from sqlalchemy.orm import sessionmaker
import polyline
from shapely.geometry import Polygon
from stravalib.model import SummaryActivity, SummaryAthlete
from src.db.models import Athlete, Map, NameSuggestion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StravaDatabase:
    def __init__(self, connection_string: str):
        engine = create_engine(connection_string)
        Base.metadata.create_all(engine)  # create the tables.
        Session = sessionmaker(bind=engine)
        self.session = Session()

    def add_auth(
        self,
        athlete_id: int,
        access_token: str,
        refresh_token: str,
        expires_at: int,
        scope: str,
    ):
        if self.session.query(Auth).filter(Auth.athlete_id == athlete_id).first():
            self.session.query(Auth).filter(Auth.athlete_id == athlete_id).update(
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "expires_at": expires_at,
                    "scope": scope,
                    "updated_at": datetime.datetime.now(),
                }
            )
            self.session.commit()
            logger.info(f"Updated auth for athlete {athlete_id}")

        else:
            auth = Auth(
                athlete_id=athlete_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                scope=scope,
                inserted_at=datetime.datetime.now(),
                updated_at=datetime.datetime.now(),
            )
            self.session.add(auth)
            self.session.commit()
            logger.info(f"Added auth for athlete {athlete_id}")

    def add_athlete(self, athlete: SummaryAthlete):
        if not self.session.query(Athlete).filter(Athlete.id == athlete.id).first():
            kwargs = {
                k: v
                for k, v in athlete.__dict__.items()
                if k in Athlete.__table__.columns.keys()
            }

            kwargs["inserted_at"] = datetime.datetime.now()
            kwargs["updated_at"] = datetime.datetime.now()

            athlete_model = Athlete(**kwargs)
            self.session.add(athlete_model)
            self.session.commit()
            logger.info(f"Added athlete {athlete.id} to the database")
        else:
            logger.info(f"Athlete with id {athlete.id} already exists in the database")

    def add_activity(self, activity: SummaryActivity):
        activity_dict = activity.model_dump()

        # process columns
        if activity_dict["start_latlng"]:
            activity_dict["start_lat"] = activity_dict["start_latlng"][0]
            activity_dict["start_lng"] = activity_dict["start_latlng"][1]
        del activity_dict["start_latlng"]

        if activity_dict["end_latlng"]:
            activity_dict["end_lat"] = activity_dict["end_latlng"][0]
            activity_dict["end_lng"] = activity_dict["end_latlng"][1]
        del activity_dict["end_latlng"]

        activity_dict["athlete_id"] = activity_dict["athlete"]["id"]
        del activity_dict["athlete"]

        # process map
        map_dict = activity_dict["map"]
        activity_dict["map_id"] = activity_dict["map"]["id"]
        del activity_dict["map"]

        activity_dict["inserted_at"] = datetime.datetime.now()
        activity_dict["updated_at"] = datetime.datetime.now()

        map = Map(**map_dict)

        # exclude attributes that are not in the model
        for k in list(activity_dict.keys()):
            if k not in Activity.__table__.columns.keys():
                del activity_dict[k]

        db_activity = Activity(**activity_dict)

        db_activity.date = activity.start_date.date()
        db_activity.time = activity.start_date.time()
        db_activity.day_of_week = activity.start_date.strftime("%A")
        db_activity.moving_time_minutes = activity.moving_time / 60
        db_activity.distance_km = activity.distance / 1000

        try:
            db_activity.pace_min_per_km = (
                1.0 * db_activity.moving_time_minutes / db_activity.distance_km
            )
        except ZeroDivisionError:
            db_activity.pace_min_per_km = None

        decoded = polyline.decode(activity.map.summary_polyline)
        if len(decoded) > 0:
            poly = Polygon(decoded)
            centroid = poly.centroid
            centroid_lat = centroid.x
            centroid_lon = centroid.y
            area = poly.area

            db_activity.map_centroid_lat = centroid_lat
            db_activity.map_centroid_lon = centroid_lon
            db_activity.map_area = area

        if not self.session.query(Map).filter(Map.id == map.id).first():
            logger.info(f"Adding map {map.id} to the database")
            self.session.add(map)
        if (
            not self.session.query(Activity)
            .filter(Activity.id == db_activity.id)
            .first()
        ):
            logger.info(f"Adding activity {db_activity.id} to the database")
            self.session.add(db_activity)
        else:
            logger.info(f"Updating activity {db_activity.id} in the database")
            existing_activity = self.session.query(Activity).filter(
                Activity.id == db_activity.id
            )
            dd = db_activity.to_dict()
            del dd["id"]
            dd["updated_at"] = datetime.datetime.now()
            existing_activity.update(dd)

        self.session.commit()

    def add_activities(self, activities: list[SummaryActivity]):
        for activity in activities:
            self.add_activity(activity)

    def add_name_suggestion(
        self, activity_id: int, name: str, description: str, probability: float
    ):
        id = self.session.query(NameSuggestion).count() + 1
        name_suggestion = NameSuggestion(
            id=id,
            activity_id=activity_id,
            name=name,
            description=description,
            probability=probability,
            inserted_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
        )
        self.session.add(name_suggestion)
        self.session.commit()

    def get_activities(
        self, athlete_id: int, after: Optional[datetime.datetime] = None
    ) -> list[Activity]:
        if after:
            return (
                self.session.query(Activity)
                .filter(Activity.athlete_id == athlete_id, Activity.start_date > after)
                .all()
            )

        return (
            self.session.query(Activity).filter(Activity.athlete_id == athlete_id).all()
        )

    def get_auth(self, athlete_id: int) -> Auth:
        return self.session.query(Auth).filter(Auth.athlete_id == athlete_id).first()

    def get_activity(self, activity_id: int) -> Activity:
        return self.session.query(Activity).filter(Activity.id == activity_id).first()

    def get_name_suggestions(self, activity_id: int) -> list[NameSuggestion]:
        return (
            self.session.query(NameSuggestion)
            .filter(NameSuggestion.activity_id == activity_id)
            .all()
        )
