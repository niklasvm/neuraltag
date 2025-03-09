from __future__ import annotations
from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    Integer,
    Float,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Time,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ToDictMixin:
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Activity(Base, ToDictMixin):
    __tablename__ = "activities"

    id = Column(BigInteger, primary_key=True)
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
    map_centroid_lat = Column(Float)
    map_centroid_lon = Column(Float)
    map_area = Column(Float)

    inserted_at = Column(DateTime)
    updated_at = Column(DateTime)

    athlete_id = Column(Integer, ForeignKey("athletes.id"))
    map_id = Column(String, ForeignKey("maps.id"))

    athlete = relationship("Athlete", back_populates="activities")
    map = relationship("Map", back_populates="activity")
    name_suggestions = relationship("NameSuggestion", back_populates="activity")


class Athlete(Base):
    __tablename__ = "athletes"

    id = Column(Integer, primary_key=True)
    resource_state = Column(Integer)
    firstname = Column(String)
    lastname = Column(String)
    profile_medium = Column(String)
    profile = Column(String)
    city = Column(String)
    state = Column(String)
    country = Column(String)
    sex = Column(String)
    premium = Column(Boolean)
    summit = Column(Boolean)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    inserted_at = Column(DateTime)

    activities = relationship("Activity", back_populates="athlete")
    auth = relationship("Auth", uselist=False, back_populates="athlete")


class Map(Base):
    __tablename__ = "maps"

    id = Column(String, primary_key=True)
    polyline = Column(String)
    summary_polyline = Column(String)
    activity = relationship(Activity.__name__, back_populates="map")

    inserted_at = Column(DateTime)
    updated_at = Column(DateTime)


class Auth(Base):
    __tablename__ = "auth"
    id = Column(Integer, primary_key=True)
    access_token = Column(String)
    refresh_token = Column(String)
    expires_at = Column(Integer)
    scope = Column(String)
    athlete_id = Column(Integer, ForeignKey("athletes.id"))
    athlete = relationship(Athlete.__name__, back_populates="auth")

    inserted_at = Column(DateTime)
    updated_at = Column(DateTime)


class NameSuggestion(Base):
    __tablename__ = "name_suggestions"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    probability = Column(Float)

    inserted_at = Column(DateTime)
    updated_at = Column(DateTime)

    activity_id = Column(BigInteger, ForeignKey("activities.id"))
    activity = relationship("Activity", back_populates="name_suggestions")
