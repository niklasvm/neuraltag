import datetime
import logging
from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker
from cryptography.fernet import Fernet
import base64

from src.app.db.models import Activity, Auth, Base, User

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
            existing_auth = (
                session.query(Auth).filter(Auth.athlete_id == auth.athlete_id).first()
            )
            if existing_auth:
                existing_auth.access_token = auth.access_token
                existing_auth.refresh_token = auth.refresh_token
                existing_auth.expires_at = auth.expires_at
                existing_auth.scope = auth.scope
                existing_auth.updated_at = datetime.datetime.now()

                session.commit()
                logger.info(f"Updated auth for athlete {auth.athlete_id}")

            else:
                session.add(auth)
                session.commit()
                logger.info(f"Added auth for athlete {auth.athlete_id}")

    def get_auth_by_athlete_id(self, athlete_id: int) -> Auth:
        with self.Session() as session:
            auth = session.query(Auth).filter(Auth.athlete_id == athlete_id).first()
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
                for k, v in activity.__dict__.items():
                    if k == "uuid":
                        continue
                    setattr(existing_activity, k, v)
                session.commit()
                logger.info(f"Updated activity {activity.activity_id}")
