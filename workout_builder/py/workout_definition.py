from __future__ import annotations
from typing import List, Optional, Literal, Union
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Annotated
from enum import Enum


# ---------- Enums ----------

class Sport(str, Enum):
    running = "running"  # limited to running only


class Intensity(str, Enum):
    warmup = "warmup"
    active = "active"
    rest = "rest"
    cooldown = "cooldown"


class DurationUnit(str, Enum):
    s = "s"
    sec = "sec"
    second = "second"
    seconds = "seconds"
    m = "m"
    min = "min"
    mins = "mins"
    minute = "minute"
    minutes = "minutes"
    km = "km"
    mtr = "m"   # optional alias if you want distance in meters (not required in YAML above)
    calories = "calories"
    cal = "cal"
    hr_greater_than = "hr_greater_than"  # threshold duration until HR > value
    hr_less_than = "hr_less_than"        # threshold duration until HR < value


class TargetTypeKind(str, Enum):
    open = "open"
    pace = "pace"
    pace_range = "pace_range"
    heart_rate_zone = "heart_rate_zone"
    heart_rate_range = "heart_rate_range"
    power_zone = "power_zone"
    power_range = "power_range"
    cadence_range = "cadence_range"


class RepeatMode(str, Enum):
    controller = "controller"  # use FIT repeat controller step
    expand = "expand"          # fully expand repetitions as concrete steps


class HROffsetMode(str, Enum):
    add_100 = "add_100"
    raw = "raw"


# ---------- Helper functions ----------

def parse_pace_str(p: Union[str, int]) -> int:
    """
    Convert 'mm:ss' pace per km to total seconds.
    Returns total seconds (int).
    """
    if isinstance(p, int):
        return p
    p_clean = p.strip()
    parts = p_clean.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid pace format '{p_clean}', expected mm:ss or integer seconds")
    mm, ss = parts
    return int(mm) * 60 + int(ss)


def pace_to_speed_scaled(pace_seconds: int) -> int:
    """
    Convert pace (sec per km) to scaled speed integer (m/s * 1000).
    speed = 1000 / pace_seconds (m/s)
    scaled int = round(speed * 1000)
    """
    if pace_seconds <= 0:
        raise ValueError("Pace seconds must be positive")
    mps = 1000.0 / pace_seconds
    return int(round(mps * 1000.0))


# ---------- Duration Spec ----------

class DurationSpec(BaseModel):
    value: Optional[Annotated[float, Field(gt=0)]] = None
    unit: Optional[DurationUnit] = None
    open: bool = False  # if true, ignore value/unit and treat as open-ended

    @field_validator("unit")
    @classmethod
    def check_unit(cls, v, info):  # info is ValidationInfo in Pydantic v2
        data = info.data  # already validated fields excluding 'unit'
        if data.get("open"):
            return v  # ignore unit if open
        if v is None:
            raise ValueError("unit required unless open=true")
        return v

    @model_validator(mode="after")
    def validate_semantics(self):
        if self.open:
            if self.value is not None:
                raise ValueError("Open duration cannot specify value")
        else:
            if self.value is None:
                raise ValueError("Duration value required when not open")
        return self

    def to_internal(self) -> dict:
        """
        Convert to internal normalized representation:
        - time_ms if time-based (seconds or minutes)
        - distance_cm if km (or optional m)
        - open flag
        """
        if self.open:
            return {"type": "open"}
        if self.unit is None:
            raise ValueError("DurationSpec.unit is None for non-open duration (validation bug)")
        unit = self.unit.value
        val = self.value
        if val is None:
            raise ValueError("DurationSpec.value is None for non-open duration (validation bug)")
        if unit in {"s", "sec", "second", "seconds"}:
            return {"type": "time", "time_ms": int(val * 1000)}
        if unit in {"m", "min", "mins", "minute", "minutes"}:
            seconds = int(val * 60)
            return {"type": "time", "time_ms": seconds * 1000}
        if unit == "km":
            # FIT distance steps use centimetres
            distance_cm = int(val * 1000 * 100)
            return {"type": "distance", "distance_cm": distance_cm}
        if unit == "m":  # optional meters if you keep it
            distance_cm = int(val * 100)
            return {"type": "distance", "distance_cm": distance_cm}
        if unit in {"calories", "cal"}:
            return {"type": "calories", "calories": int(val)}
        if unit == "hr_greater_than":
            return {"type": "hr_greater_than", "bpm": int(val)}
        if unit == "hr_less_than":
            return {"type": "hr_less_than", "bpm": int(val)}
        raise ValueError(f"Unsupported duration unit '{unit}'")


# ---------- Target Specs ----------

class BaseTarget(BaseModel):
    type: TargetTypeKind
    model_config = ConfigDict(extra='forbid')

    def to_internal(self, hr_offset_mode: HROffsetMode) -> dict:
        raise NotImplementedError


class OpenTarget(BaseTarget):
    type: Literal[TargetTypeKind.open] = TargetTypeKind.open

    def to_internal(self, hr_offset_mode: HROffsetMode) -> dict:
        return {"kind": "open"}


class PaceTarget(BaseTarget):
    type: Literal[TargetTypeKind.pace] = TargetTypeKind.pace
    value: Union[str, int]  # "mm:ss" or total seconds
    unit: Literal["min_per_km"]

    def to_internal(self, hr_offset_mode: HROffsetMode) -> dict:
        total_sec = parse_pace_str(self.value)
        speed_scaled = pace_to_speed_scaled(total_sec)
        return {"kind": "pace", "low": speed_scaled, "high": speed_scaled}


class PaceRangeTarget(BaseTarget):
    type: Literal[TargetTypeKind.pace_range] = TargetTypeKind.pace_range
    low: Union[str, int]
    high: Union[str, int]
    unit: Literal["min_per_km"]

    @model_validator(mode="after")
    def validate_pace_range(self):
        if self.low is None or self.high is None:
            raise ValueError("low and high required for pace_range")
        return self

    def to_internal(self, hr_offset_mode: HROffsetMode) -> dict:
        low_sec = parse_pace_str(self.low)
        high_sec = parse_pace_str(self.high)
        # Note: faster pace => smaller seconds => larger speed
        low_speed = pace_to_speed_scaled(high_sec)  # high pace sec -> slower -> lower speed
        high_speed = pace_to_speed_scaled(low_sec)  # low pace sec -> faster -> higher speed
        if low_speed > high_speed:
            # ensure ascending
            low_speed, high_speed = high_speed, low_speed
        return {"kind": "pace_range", "low": low_speed, "high": high_speed}


class HRZoneTarget(BaseTarget):
    type: Literal[TargetTypeKind.heart_rate_zone] = TargetTypeKind.heart_rate_zone
    zone: Annotated[int, Field(gt=0)]

    def to_internal(self, hr_offset_mode: HROffsetMode) -> dict:
        return {"kind": "hr_zone", "zone": self.zone}


class HRRangeTarget(BaseTarget):
    type: Literal[TargetTypeKind.heart_rate_range] = TargetTypeKind.heart_rate_range
    low: Annotated[int, Field(gt=0)]
    high: Annotated[int, Field(gt=0)]
    unit: Literal["bpm"]

    @model_validator(mode="after")
    def validate_hr_range(self):
        if self.low >= self.high:
            raise ValueError("heart_rate_range low must be < high")
        return self

    def to_internal(self, hr_offset_mode: HROffsetMode) -> dict:
        if hr_offset_mode == HROffsetMode.add_100:
            low = self.low + 100
            high = self.high + 100
        else:
            low, high = self.low, self.high
        return {"kind": "hr_range", "low": low, "high": high}


class PowerZoneTarget(BaseTarget):
    type: Literal[TargetTypeKind.power_zone] = TargetTypeKind.power_zone
    zone: Annotated[int, Field(gt=0)]

    def to_internal(self, hr_offset_mode: HROffsetMode) -> dict:
        return {"kind": "power_zone", "zone": self.zone}


class PowerRangeTarget(BaseTarget):
    type: Literal[TargetTypeKind.power_range] = TargetTypeKind.power_range
    low: Annotated[int, Field(gt=0)]
    high: Annotated[int, Field(gt=0)]
    unit: Literal["watts"]

    @model_validator(mode="after")
    def validate_power_range(self):
        if self.low >= self.high:
            raise ValueError("power_range low must be < high")
        return self

    def to_internal(self, hr_offset_mode: HROffsetMode) -> dict:
        return {"kind": "power_range", "low": self.low, "high": self.high}


class CadenceRangeTarget(BaseTarget):
    type: Literal[TargetTypeKind.cadence_range] = TargetTypeKind.cadence_range
    low: Annotated[int, Field(gt=0)]
    high: Annotated[int, Field(gt=0)]
    unit: Literal["rpm"]

    @model_validator(mode="after")
    def validate_cadence_range(self):
        if self.low >= self.high:
            raise ValueError("cadence_range low must be < high")
        return self

    def to_internal(self, hr_offset_mode: HROffsetMode) -> dict:
        return {"kind": "cadence_range", "low": self.low, "high": self.high}


Target = Annotated[
    Union[
        OpenTarget,
        PaceTarget,
        PaceRangeTarget,
        HRZoneTarget,
        HRRangeTarget,
        PowerZoneTarget,
        PowerRangeTarget,
        CadenceRangeTarget,
    ],
    Field(discriminator='type')
]


# ---------- Step Models ----------

class BaseStep(BaseModel):
    name: Optional[str] = None
    intensity: Optional[Intensity] = None
    model_config = ConfigDict(extra='forbid')


class SimpleStep(BaseStep):
    type: Literal["simple"] = "simple"
    # duration now optional; if omitted treat as open
    duration: Optional[DurationSpec] = None
    # target optional; if omitted treat as open
    target: Optional[Target] = None
    note: Optional[str] = None

    def to_internal(self, idx: int, defaults: dict) -> List[dict]:
        inten = self.intensity or defaults.get("default_intensity", Intensity.active)
        # If duration missing, default to open
        duration_norm = self.duration.to_internal() if self.duration else {"type": "open"}
        target_norm = (
            self.target.to_internal(defaults["hr_offset_mode"])
            if self.target is not None
            else {"kind": "open"}
        )
        return [{
            "index": idx,
            "kind": "simple",
            "name": self.name or f"Step {idx}",
            "intensity": inten.value,
            "duration": duration_norm,
            "target": target_norm,
            **({"note": self.note} if self.note else {})
        }]


class GroupStep(BaseStep):
    type: Literal["group"] = "group"
    repeat: Optional[int] = None            # total sets desired
    mode: Optional[RepeatMode] = None
    children: List[SimpleStep]

    def to_internal(self, start_idx: int, defaults: dict) -> List[dict]:
        mode = self.mode or defaults.get("repeat_mode_default", RepeatMode.controller)
        rep = self.repeat
        results = []
        base_index = start_idx

        # Add the first block
        child_idx = base_index
        first_block_indices = []
        for child in self.children:
            for built in child.to_internal(child_idx, defaults):
                results.append(built)
                first_block_indices.append(built["index"])
                child_idx += 1

        if rep and rep > 1:
            if mode == RepeatMode.controller:
                # Insert a repeat controller referencing the first child index
                from_index = first_block_indices[0]
                repeat_controller = {
                    "index": child_idx,
                    "kind": "repeat_controller",
                    "repeat_from": from_index,
                    "additional_times": rep - 1  # FIT expects extra times
                }
                results.append(repeat_controller)
            else:
                # Expand physically
                for _ in range(rep - 1):
                    for child in self.children:
                        for built in child.to_internal(child_idx, defaults):
                            results.append(built)
                            child_idx += 1
        return results


class RepeatRefStep(BaseStep):
    """
    Alternative pattern if you wanted referencing anchors (not used in YAML example above).
    Left as placeholder; you can extend later.
    """
    type: Literal["repeat"] = "repeat"
    from_anchor: str
    steps_count: int
    repeat: int

    def to_internal(self, idx: int, defaults: dict):
        raise NotImplementedError("Anchor-based repeat not implemented in this prototype")


WorkoutStep = Annotated[Union[SimpleStep, GroupStep], Field(discriminator='type')]


# ---------- Options & Metadata ----------

class WorkoutOptions(BaseModel):
    hr_offset_mode: HROffsetMode = HROffsetMode.add_100
    default_intensity: Intensity = Intensity.active
    repeat_mode_default: RepeatMode = RepeatMode.controller


class WorkoutMetadata(BaseModel):
    name: str
    description: Optional[str] = None
    sport: Sport
    @field_validator("sport")
    @classmethod
    def enforce_running(cls, v):
        if v != Sport.running:
            raise ValueError("Only 'running' sport supported in this schema.")
        return v


# ---------- Root Model ----------

class WorkoutDefinition(BaseModel):
    version: Annotated[int, Field(ge=1)] = 1
    metadata: WorkoutMetadata
    options: WorkoutOptions = Field(default_factory=WorkoutOptions)
    steps: List[WorkoutStep]

    @model_validator(mode="before")
    @classmethod
    def inject_step_types(cls, data):
        # When loading from YAML users likely omit explicit 'type' for simple/group
        raw_steps = data.get('steps') if isinstance(data, dict) else None
        if isinstance(raw_steps, list):
            new_steps = []
            for s in raw_steps:
                if isinstance(s, dict) and 'type' not in s:
                    if 'children' in s:
                        s = {**s, 'type': 'group'}
                    else:
                        s = {**s, 'type': 'simple'}
                new_steps.append(s)
            data['steps'] = new_steps
        return data
    @model_validator(mode="after")
    def validate_steps_nonempty(self):
        if not self.steps:
            raise ValueError("At least one step is required.")
        return self

    def expand(self) -> List[dict]:
        """
        Produce a flattened list of internal step dictionaries with assigned indexes.
        """
        internal = []
        idx = 0
        defaults = {
            "hr_offset_mode": self.options.hr_offset_mode,
            "default_intensity": self.options.default_intensity,
            "repeat_mode_default": self.options.repeat_mode_default
        }
        for step in self.steps:
            if isinstance(step, SimpleStep):
                built = step.to_internal(idx, defaults)
                internal.extend(built)
                idx += len(built)
            elif isinstance(step, GroupStep):
                built = step.to_internal(idx, defaults)
                internal.extend(built)
                idx = max(s["index"] for s in built) + 1 if built else idx
            else:
                raise ValueError(f"Unsupported step type in expansion: {step}")
        # Reassign sequential indexes to ensure contiguous messageIndex
        for new_i, s in enumerate(internal):
            s["index"] = new_i
        return internal

    def summary(self) -> dict:
        expanded = self.expand()
        return {
            "name": self.metadata.name,
            "sport": self.metadata.sport.value,
            "total_steps": len(expanded),
            "steps": expanded
        }


# ---------- Example Usage (not executed automatically) ----------

if __name__ == "__main__":
        import yaml
        file = "/Users/niklasvonmaltzahn/Documents/personal/neuraltag/workout_builder/example_workout_3.yml"
        
        with open(file, 'r') as f:
                data = yaml.safe_load(f)
        
        workout = WorkoutDefinition(**data)
        print(workout.summary())
    # print json schema
    # print(WorkoutDefinition.model_json_schema())
    
# ---

# ## How You’d Use This

# 1. `pip install pydantic pyyaml`
# 2. Load YAML → `WorkoutDefinition(**yaml.safe_load(f))`
# 3. Call `expand()` to get normalized step list
# 4. Translate each internal dict to FIT `WorkoutStepMesg` (straightforward mapping)
# 5. Use your existing FIT encoding code (FileIdMesg + WorkoutMesg + steps)

# ---

# ## Mapping Internal Expanded Step to FIT (Conceptual)

# For each expanded dict (example):