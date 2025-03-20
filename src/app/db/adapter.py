import datetime
import logging
import uuid
from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker
from cryptography.fernet import Fernet
import base64

from src.app.db.models import Activity, Auth, Base, NameSuggestion, User
from sqlalchemy import insert

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ACTIVITY_COLUMNS_TO_ENCRYPT = [
#     "start_lat",
#     "start_lng",
#     "end_lat",
#     "end_lng",
#     "map_summary_polyline",
#     "map_centroid_lat",
#     "map_centroid_lon",
#     "location_city",
#     "location_state",
#     "location_country",
#     "name",
# ]


def encrypt_token(token: str, key: bytes) -> str:
    """Encrypts an access token."""
    f = Fernet(key)
    encrypted_token = f.encrypt(token.encode())
    return base64.urlsafe_b64encode(encrypted_token).decode()


def decrypt_token(encrypted_token: str, key: bytes) -> str:
    """Decrypts an access token."""
    f = Fernet(key)
    encrypted_token_bytes = base64.urlsafe_b64decode(encrypted_token)
    decrypted_token = f.decrypt(encrypted_token_bytes).decode()
    return decrypted_token


class Database:
    def __init__(self, connection_string: str, encryption_key: bytes):
        engine = create_engine(connection_string)
        Base.metadata.create_all(engine)  # create the tables.
        self.Session = sessionmaker(bind=engine)

        self.encryption_key = encryption_key

    def add_user(self, user: User):
        with self.Session() as session:
            existing_user = (
                session.query(User).filter(User.athlete_id == user.athlete_id).first()
            )
            if not existing_user:
                session.add(user)
                session.commit()
                logger.info(f"Added user {user.uuid} to the database")

                return str(user.uuid)

            logger.info(
                f"User with id {existing_user.uuid} already exists in the database"
            )
            return str(existing_user.uuid)

    def get_user(self, uuid: str) -> User:
        with self.Session() as session:
            return session.query(User).filter(User.uuid == uuid).first()

    def add_auth(self, auth: Auth):
        # encrypt tokens
        auth.access_token = encrypt_token(auth.access_token, self.encryption_key)
        auth.refresh_token = encrypt_token(auth.refresh_token, self.encryption_key)

        with self.Session() as session:
            existing_auth = session.query(Auth).filter(Auth.uuid == auth.uuid).first()
            if existing_auth:
                existing_auth.access_token = auth.access_token
                existing_auth.refresh_token = auth.refresh_token
                existing_auth.expires_at = auth.expires_at
                existing_auth.scope = auth.scope
                existing_auth.updated_at = datetime.datetime.now()

                session.commit()
                logger.info(f"Updated auth {auth.uuid}")

            else:
                session.add(auth)
                session.commit()
                logger.info(f"Added auth for {auth.uuid} to the database")

    def get_auth(self, uuid: int) -> Auth:
        with self.Session() as session:
            auth = session.query(Auth).filter(Auth.uuid == uuid).first()
            auth.access_token = decrypt_token(auth.access_token, self.encryption_key)
            auth.refresh_token = decrypt_token(auth.refresh_token, self.encryption_key)
            return auth

    def get_auth_by_athlete_id(self, athlete_id: int) -> Auth:
        with self.Session() as session:
            auth = (
                session.query(Auth)
                .join(User)
                .filter(User.athlete_id == athlete_id)
                .first()
            )
            auth.access_token = decrypt_token(auth.access_token, self.encryption_key)
            auth.refresh_token = decrypt_token(auth.refresh_token, self.encryption_key)
            return auth

    def add_activity(self, activity: Activity):
        with self.Session() as session:
            existing_activity = (
                session.query(Activity)
                .filter(Activity.activity_id == activity.activity_id)
                .first()
            )
            if not existing_activity:
                session.add(activity)
                session.commit()
                logger.info(f"Added activity {activity.activity_id} to the database")
            else:
                # update all fields with a loop
                for key, value in activity.dict().items():
                    if key not in ["uuid", "activity_id", "created_at", "updated_at"]:
                        setattr(existing_activity, key, value)
                existing_activity.updated_at = datetime.datetime.now()
                session.commit()

    def add_activities_bulk(self, activities: list[Activity]):
        with self.Session() as session:
            existing_activity_ids = session.query(Activity.activity_id).all()
            existing_activity_ids = [x[0] for x in existing_activity_ids]

            activities = [
                activity
                for activity in activities
                if activity.activity_id not in existing_activity_ids
            ]
            for activity in activities:
                activity.uuid = str(uuid.uuid4())
                activity.created_at = datetime.datetime.now()
                activity.updated_at = datetime.datetime.now()

            session.execute(
                insert(Activity).values([activity.dict() for activity in activities])
            )
            session.commit()
            logger.info(f"Added {len(activities)} activities to the database")

    def get_activities_by_date_range(
        self, athlete_id: int, before: datetime.datetime, after: datetime.datetime
    ) -> list[Activity]:
        with self.Session() as session:
            return (
                session.query(Activity)
                .filter(
                    Activity.athlete_id == athlete_id,
                    Activity.start_date_local <= before,
                    Activity.start_date_local >= after,
                )
                .all()
            )

    def delete_user(self, athlete_id: int):
        with self.Session() as session:
            user = session.query(User).filter(User.athlete_id == athlete_id).first()
            if user:
                session.delete(user)
                session.commit()
                logger.info(f"Deleted user {athlete_id}")


    def add_name_suggestion(self,name_suggestion: NameSuggestion):
        with self.Session() as session:
            session.add(name_suggestion)
            session.commit()
            logger.info(f"Added name suggestion {name_suggestion.activity_id} to the database")