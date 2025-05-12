import datetime
import logging
import uuid
from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker
from cryptography.fernet import Fernet
import base64

from src.database.models import (
    Activity,
    Auth,
    Base,
    NameSuggestion,
    PromptResponse,
    RenameHistory,
    User,
)
from sqlalchemy import insert

logger = logging.getLogger(__name__)

USER_ENCRYPTED_COLUMNS = [
    "name",
    "lastname",
    "sex",
    "city",
    "profile",
    "profile_medium",
    "state",
    "country",
]


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
        for column in USER_ENCRYPTED_COLUMNS:
            if hasattr(user, column):
                value = getattr(user, column)
                if value:
                    encrypted_value = encrypt_token(value, self.encryption_key)
                    setattr(user, column, encrypted_value)

        with self.Session() as session:
            existing_user = (
                session.query(User).filter(User.athlete_id == user.athlete_id).first()
            )
            if not existing_user:
                session.add(user)
                session.commit()
                logger.info(f"Added user {user.uuid} to the database")

                return str(user.uuid)
            else:
                existing_user.updated_at = datetime.datetime.now()
                existing_user.athlete_id = user.athlete_id
                existing_user.auth_uuid = user.auth_uuid

                model_columns = [
                    x.name
                    for x in existing_user.__table__.columns
                    if x.name not in ["uuid", "created_at", "updated_at"]
                ]
                for column in model_columns:
                    setattr(existing_user, column, getattr(user, column))

                session.commit()

            logger.info(
                f"User with id {existing_user.uuid} already exists in the database"
            )
            return str(existing_user.uuid)

    def get_user(self, uuid: str) -> User:
        with self.Session() as session:
            user = session.query(User).filter(User.uuid == uuid).first()

        for column in USER_ENCRYPTED_COLUMNS:
            if hasattr(user, column):
                value = getattr(user, column)
                if value:
                    decrypted_value = decrypt_token(value, self.encryption_key)
                    setattr(user, column, decrypted_value)
        return user

    def get_user_by_auth_id(self, auth_id: str) -> User:
        with self.Session() as session:
            user = session.query(User).filter(User.auth_uuid == auth_id).first()
            if not user:
                logger.info(f"User with auth id {auth_id} not found")
                return None
            for column in USER_ENCRYPTED_COLUMNS:
                if hasattr(user, column):
                    value = getattr(user, column)
                    if value:
                        decrypted_value = decrypt_token(value, self.encryption_key)
                        setattr(user, column, decrypted_value)
            return user

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

    def get_activity_by_id(self, activity_id: int) -> Activity:
        with self.Session() as session:
            activity = (
                session.query(Activity)
                .filter(Activity.activity_id == activity_id)
                .first()
            )
            if activity:
                return activity
            else:
                logger.info(f"Activity {activity_id} not found")
                raise ValueError(f"Activity {activity_id} not found")

    def delete_user(self, athlete_id: int):
        with self.Session() as session:
            user = session.query(User).filter(User.athlete_id == athlete_id).first()
            if user:
                session.delete(user)
                session.commit()
                logger.info(f"Deleted user {athlete_id}")

    def delete_auth(self, uuid: str):
        with self.Session() as session:
            auth = session.query(Auth).filter(Auth.uuid == uuid).first()
            if auth:
                session.delete(auth)
                session.commit()
                logger.info(f"Deleted auth {uuid}")

    def add_name_suggestion(self, name_suggestion: NameSuggestion):
        with self.Session() as session:
            session.add(name_suggestion)
            session.commit()
            logger.info(
                f"Added name suggestion {name_suggestion.activity_id} to the database"
            )

    def delete_activity(self, activity_id: int, athlete_id: int):
        with self.Session() as session:
            activity = (
                session.query(Activity)
                .filter(
                    Activity.activity_id == activity_id,
                    Activity.athlete_id == athlete_id,
                )
                .first()
            )
            if activity:
                session.delete(activity)
                session.commit()
                logger.info(f"Deleted activity {activity_id}")

    def add_prompt_response(self, prompt_response: PromptResponse):
        with self.Session() as session:
            session.add(prompt_response)
            session.commit()
            logger.info(f"Added prompt response {prompt_response.uuid} to the database")

    def add_rename_history(self, old_name: str, new_name: str, activity_id: int):
        rename_history = RenameHistory(
            old_name=old_name,
            new_name=new_name,
            activity_id=activity_id,
        )
        with self.Session() as session:
            session.add(rename_history)
            session.commit()
            logger.info(
                f"Added rename history {rename_history.activity_id} to the database"
            )

    def get_name_suggestions_by_activity_id(
        self, activity_id: int
    ) -> list[NameSuggestion]:
        with self.Session() as session:
            # get the latest prompt response for the activity and order by created_at at get the latest name suggestions
            prompt_response = (
                session.query(PromptResponse)
                .filter(PromptResponse.activity_id == activity_id)
                .order_by(PromptResponse.created_at.desc())
                .first()
            )
            if not prompt_response:
                logger.info(f"No prompt response found for activity {activity_id}")
                return []
            name_suggestions = prompt_response.name_suggestions
            return name_suggestions

    def get_last_rename(self, activity_id: int) -> None | RenameHistory:
        with self.Session() as session:
            rename_history = (
                session.query(RenameHistory)
                .filter(RenameHistory.activity_id == activity_id)
                .order_by(RenameHistory.created_at.desc())
                .first()
            )
            if not rename_history:
                logger.info(f"No rename history found for activity {activity_id}")
                return None
            return rename_history
