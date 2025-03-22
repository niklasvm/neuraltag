from __future__ import annotations
import datetime
import uuid
from sqlalchemy import (
    UUID,
    BigInteger,
    Boolean,
    Column,
    Date,
    Float,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Time,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Auth(Base):
    __tablename__ = "auth"
    uuid = Column(UUID, primary_key=True, nullable=False, default=uuid.uuid4)
    access_token = Column(String)
    refresh_token = Column(String)
    expires_at = Column(Integer)
    scope = Column(String)
    user = relationship("User", back_populates="auth")

    created_at = Column(DateTime, nullable=False, default=datetime.datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.now)


class User(Base):
    __tablename__ = "user"

    uuid = Column(UUID, primary_key=True, nullable=False, default=uuid.uuid4)
    athlete_id = Column(Integer, unique=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.now)
    updated_at = Column(DateTime)
    auth_uuid = Column(UUID, ForeignKey("auth.uuid"))
    auth = relationship("Auth", back_populates="user")
    activity = relationship(
        "Activity", back_populates="user", cascade="all, delete-orphan"
    )


class Activity(Base):
    __tablename__ = "activity"
    uuid = Column(UUID, primary_key=True, nullable=False, default=uuid.uuid4)
    athlete_id = Column(Integer, ForeignKey("user.athlete_id"))
    user = relationship(User.__name__, back_populates="activity")
    name_suggestions = relationship("NameSuggestion", back_populates="activity")
    prompt_responses = relationship(
        "PromptResponse", back_populates="activity", cascade="all, delete-orphan"
    )

    activity_id = Column(BigInteger, unique=True)
    description = Column(String, nullable=True)
    achievement_count = Column(Integer)
    athlete_count = Column(Integer)
    average_speed = Column(Float)
    average_watts = Column(Float, nullable=True)
    comment_count = Column(Integer)
    commute = Column(Boolean)
    device_watts = Column(Boolean, nullable=True)
    distance = Column(Float)
    elapsed_time = Column(Integer)
    elev_high = Column(Float)
    elev_low = Column(Float)
    end_lat = Column(Float)
    end_lng = Column(Float)
    external_id = Column(String)
    flagged = Column(Boolean)
    gear_id = Column(String)
    has_kudoed = Column(Boolean)
    hide_from_home = Column(Boolean, nullable=True)
    kilojoules = Column(Float, nullable=True)
    kudos_count = Column(Integer)
    manual = Column(Boolean)
    max_speed = Column(Float)
    max_watts = Column(Float, nullable=True)
    moving_time = Column(Integer)
    name = Column(String)
    photo_count = Column(Integer)
    private = Column(Boolean)
    sport_type = Column(String)
    start_date = Column(DateTime)
    start_date_local = Column(DateTime)
    start_lat = Column(Float)
    start_lng = Column(Float)
    timezone = Column(String)
    total_elevation_gain = Column(Float)
    total_photo_count = Column(Integer)
    trainer = Column(Boolean)
    type = Column(String)
    upload_id = Column(BigInteger)
    upload_id_str = Column(String)
    weighted_average_watts = Column(Float, nullable=True)
    workout_type = Column(Integer)
    utc_offset = Column(Float)
    location_city = Column(String, nullable=True)
    location_state = Column(String, nullable=True)
    location_country = Column(String)
    pr_count = Column(Integer)
    suffer_score = Column(Integer)
    has_heartrate = Column(Boolean)
    average_heartrate = Column(Float)
    max_heartrate = Column(Integer)
    average_cadence = Column(Float)
    from_accepted_tag = Column(Boolean)
    visibility = Column(String)
    date = Column(Date)
    time = Column(Time)
    day_of_week = Column(String)
    moving_time_minutes = Column(Float)
    distance_km = Column(Float)
    pace_min_per_km = Column(Float)
    map_summary_polyline = Column(String)
    map_centroid_lat = Column(Float)
    map_centroid_lon = Column(Float)
    map_area = Column(Float)

    created_at = Column(DateTime, nullable=False, default=datetime.datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.now)

    def dict(self):
        d = {}
        for column in self.__table__.columns:
            d[column.name] = getattr(self, column.name)
        return d


class PromptResponse(Base):
    __tablename__ = "prompt_response"
    uuid = Column(UUID, primary_key=True, nullable=False, default=uuid.uuid4)
    activity_id = Column(BigInteger, ForeignKey("activity.activity_id"))
    activity = relationship(Activity.__name__)
    prompt = Column(String)
    response = Column(String)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.now)


class NameSuggestion(Base):
    __tablename__ = "name_suggestion"
    uuid = Column(UUID, primary_key=True, nullable=False, default=uuid.uuid4)
    activity_id = Column(BigInteger, ForeignKey("activity.activity_id"))
    activity = relationship(Activity.__name__)
    name = Column(String)
    description = Column(String)
    probability = Column(Float)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.now)
