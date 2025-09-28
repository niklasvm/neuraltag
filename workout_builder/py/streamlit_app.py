import tempfile
import shutil
from pathlib import Path
from typing import Optional
import yaml
import streamlit as st
import pandas as pd
import re
from workout_builder.py.workout_definition import WorkoutDefinition
from workout_builder.py.header_logger import HeaderLogger
from pydantic_ai import Agent
from dotenv import load_dotenv


load_dotenv(override=True)

# model="google-gla:gemma-3-27b-it"
model="google-gla:gemini-2.5-flash-lite"

# Initialize header logger
logger = HeaderLogger("workout_headers.jsonl")

# Log page visit on first load
if 'page_visited' not in st.session_state:
    logger.log_event('page_visit')
    st.session_state.page_visited = True

# ---------------- Helper logic (inlined from notebook) ---------------- #


def _sanitize_name(n: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 _-]", "", n)[:30]
    return cleaned.replace(" ", "_")


def generate_workout(
    workout_description: str,
    workout_name: Optional[str] = None,
    model: str = "google-gla:gemini-2.5-flash-lite",
    use_structured_output: bool = False,
) -> WorkoutDefinition:
    schema = WorkoutDefinition.model_json_schema()

    if workout_name:
        name_instruction = f"Use the exact workout name: '{workout_name}'"
    else:
        name_instruction = "Provide the workout a creative name"

    system_prompt = f"""You are a helpful assistant that helps translate user requests into structured workout definitions.
    {name_instruction} and description. Steps should also be creatively named with appropriate descriptions and notes
    """

    if not use_structured_output:
        system_prompt = f"""
        {system_prompt}.
        Use the json schema for the output:
        ```
        {schema}
        ```
        
        """
        agent = Agent(model=model)
        prompt = (
            f"""Help me generate a json file for the workout: {workout_description}"""
        )
        result = agent.run_sync(system_prompt + prompt)

        # extract text between markdown code blocks
        match = re.search(r"```(json)?\n(.*?)\n```", result.output, re.DOTALL)
        if match:
            json_text = match.group(2)
            result.output = json_text
        else:
            print("No code block found")

        try:
            workout: WorkoutDefinition = WorkoutDefinition.model_validate_json(
                json_text
            )
        except Exception:
            print("Failed to parse JSON, falling back to structured output")
            print(json_text)
            # Fall back to structured output
            agent = Agent(model=model, system_prompt=system_prompt)
            prompt = f"""Help me generate a workout for: {workout_description}"""
            result = agent.run_sync(prompt, output_type=WorkoutDefinition)
            workout = result.output
    else:
        agent = Agent(model=model, system_prompt=system_prompt)
        prompt = f"""Help me generate a workout for: {workout_description}"""
        result = agent.run_sync(prompt, output_type=WorkoutDefinition)

        workout = result.output

    # Override the workout name if one was provided by the user
    if workout_name and workout_name.strip():
        workout.metadata.name = workout_name.strip()

    print(f"💡 Created workout: {workout.metadata.name}")
    return workout


def encode_to_fit(yaml_file: str, fit_file: str):
    """Encode a YAML workout to FIT using Java encoder without passing an explicit name.
    NOTE: This assumes the Java build & jars are already present."""
    import workout_builder

    JAVA_DIR = Path(workout_builder.__file__).parent / "java"
    JAVA_BUILD = JAVA_DIR / "build"
    JAVA_LIB_DIR = JAVA_DIR / "lib"
    FIT_JAR = JAVA_LIB_DIR / "fit.jar"
    SNAKEYAML_JAR = JAVA_LIB_DIR / "snakeyaml-2.2.jar"
    CLASSPATH = ":".join([str(JAVA_BUILD), str(FIT_JAR), str(SNAKEYAML_JAR)])
    ENCODER_CLASS = "com.neuraltag.workout.EncodeYamlWorkout"
    # read metadata name to predict filename
    with open(yaml_file, "r") as yf:
        data = yaml.safe_load(yf)
    meta_name = data.get("metadata", {}).get("name", "Workout")
    produced_filename = f"{_sanitize_name(meta_name)}.fit"
    import subprocess

    subprocess.run(
        f"java -cp {CLASSPATH} {ENCODER_CLASS} {yaml_file}", shell=True, check=True
    )
    shutil.move(produced_filename, fit_file)


st.set_page_config(page_title="Workout Builder", layout="wide",page_icon="src/app/static/images/favicon.ico")

st.title("🏃 Workout Builder & FIT Generator")

# Simplified UI (no advanced model/HR/structured controls)
st.caption(
    f"Enter a the description of the workout you want to generate. The app uses `{model}` under the hood to build a structured workout definition, encodes it to FIT, and lets you download the file for your Garmin device."
)

workout_name = st.text_input(
    "Workout Name",
    placeholder="Enter a name for your workout (e.g. Speed Intervals, Long Run, etc.)",
    help="This will be the name displayed on your Garmin device"
)

prompt = st.text_area(
    "Workout Prompt",
    height=200,
    placeholder="Describe the workout (e.g. 10min warmup, 6x1km @4:00-4:05/km w/90s rest, 10min cooldown)",
)

# Log input changes (simple detection)
if workout_name and workout_name != st.session_state.get('prev_workout_name', ''):
    logger.log_event('input_change', {'field': 'workout_name', 'has_value': bool(workout_name.strip())})
    st.session_state.prev_workout_name = workout_name

if prompt and prompt != st.session_state.get('prev_prompt', ''):
    logger.log_event('input_change', {'field': 'workout_prompt', 'char_count': len(prompt)})
    st.session_state.prev_prompt = prompt

generate_btn = st.button("Generate Workout", type="primary")

if "workout_def" not in st.session_state:
    st.session_state.workout_def = None
if "fit_bytes" not in st.session_state:
    st.session_state.fit_bytes = None
if "fit_filename" not in st.session_state:
    st.session_state.fit_filename = None

if generate_btn:
    logger.log_event('button_click', {'button': 'generate_workout'})
    
    if not prompt.strip():
        logger.log_event('validation_error', {'error': 'empty_prompt'})
        st.warning("Please enter a workout prompt first.")
    elif not workout_name.strip():
        logger.log_event('validation_error', {'error': 'empty_workout_name'})
        st.warning("Please enter a workout name first.")
    else:
        with st.spinner("Generating workout..."):
            try:
                logger.log_event('generation_start', {
                    'workout_name': workout_name,
                    'prompt_length': len(prompt),
                    'model': "google-gla:gemma-3-27b-it"
                })
                
                workout_def = generate_workout(
                    prompt, workout_name=workout_name,
                    model=model,
                )
                
                logger.log_event('generation_success', {
                    'workout_name': workout_def.metadata.name,
                    'steps_count': len(workout_def.steps) if hasattr(workout_def, 'steps') else 0
                })
                
                st.session_state.workout_def = workout_def
                tmp_dir = Path(tempfile.mkdtemp(prefix="workout_fit_"))
                yaml_path = tmp_dir / "workout.yaml"
                fit_path = tmp_dir / "workout.fit"
                yaml_text_local = yaml.safe_dump(
                    workout_def.model_dump(mode="json", exclude_none=True),
                    sort_keys=False,
                    indent=2,
                )
                with open(yaml_path, "w") as f:
                    f.write(yaml_text_local)
                try:
                    encode_to_fit(str(yaml_path), str(fit_path))
                    st.session_state.fit_bytes = fit_path.read_bytes()
                    st.session_state.fit_filename = (
                        f"{_sanitize_name(workout_def.metadata.name)}.fit"
                    )
                    
                    logger.log_event('fit_generation_success', {
                        'filename': st.session_state.fit_filename,
                        'file_size': len(st.session_state.fit_bytes)
                    })
                    
                finally:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception as e:
                logger.log_event('generation_error', {
                    'error_message': str(e),
                    'error_type': type(e).__name__
                })
                st.error(f"Generation failed: {e}")

workout_def = st.session_state.workout_def

if workout_def:
    st.success(f"Generated: {workout_def.metadata.name}")

    # Download button directly under generation controls
    if st.session_state.fit_bytes:
        if st.download_button(
            "Download FIT File",
            data=st.session_state.fit_bytes,
            file_name=st.session_state.fit_filename or "workout.fit",
            mime="application/octet-stream",
        ):
            logger.log_event('fit_download', {
                'filename': st.session_state.fit_filename,
                'file_size': len(st.session_state.fit_bytes),
                'workout_name': workout_def.metadata.name
            })
    else:
        st.warning("FIT file not available.")

    # Expanded steps full width first
    def expand_to_df(w: WorkoutDefinition) -> pd.DataFrame:
        rows = []
        for step in w.expand():
            # Skip controller/group repeat steps for display purposes only
            kind_val = step.get("kind") or ""
            if kind_val in {"repeat", "group", "repeat_controller", "controller"}:
                continue
            d = step.get("duration", {})
            t = step.get("target", {})
            dur_type = d.get("type")
            if dur_type == "time":
                total_seconds = int(round(d["time_ms"] / 1000))
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                if hours > 0:
                    dur_display = f"{hours:01d}:{minutes:02d}:{seconds:02d}"
                else:
                    dur_display = (
                        f"{minutes:02d}:{seconds:02d}"  # mm:SS when under 1 hour
                    )
            elif dur_type == "distance":
                km = d["distance_cm"] / 100 / 1000
                dur_display = f"{km:.2f} km"
            elif dur_type == "calories":
                dur_display = f"{d['calories']} cal"
            elif dur_type == "hr_greater_than":
                dur_display = f"HR > {d['bpm']}"
            elif dur_type == "hr_less_than":
                dur_display = f"HR < {d['bpm']}"
            else:
                dur_display = dur_type
            target_kind = t.get("kind") or t.get("zone")
            if target_kind in ("pace", "pace_range"):
                low = t.get("low")
                high = t.get("high")

                def speed_to_pace(s):
                    if not s:
                        return None
                    mps = s / 1000.0
                    if mps == 0:
                        return None
                    sec_per_km = 1000.0 / mps
                    mins = int(sec_per_km // 60)
                    secs = int(round(sec_per_km % 60))
                    return f"{mins}:{secs:02d}"

                if target_kind == "pace":
                    tgt_display = speed_to_pace(low)
                else:
                    tgt_display = f"{speed_to_pace(low)} - {speed_to_pace(high)}"
            elif target_kind in ("hr_range", "cadence_range", "power_range"):
                tgt_display = f"{t.get('low')}-{t.get('high')}"
            elif target_kind == "hr_zone":
                tgt_display = f"Zone {t.get('zone')}"
            elif target_kind == "power_zone":
                tgt_display = f"Power Z{t.get('zone')}"
            elif target_kind == "open" or target_kind is None:
                tgt_display = "Open"
            else:
                tgt_display = target_kind
            rows.append(
                {
                    "index": step["index"],
                    "name": step.get("name"),
                    "kind": step.get("kind"),
                    "intensity": step.get("intensity"),
                    "duration_type": dur_type,
                    "duration": dur_display,
                    "target": tgt_display,
                    "note": step.get("note"),
                }
            )
        return pd.DataFrame(rows)

    # st.subheader("Expanded Steps")
    # st.dataframe(expand_to_df(workout_def), use_container_width=True)

    # YAML removed per simplified UI request
else:
    st.info("Enter a prompt and click 'Generate Workout' to begin.")

# Show YAML at absolute bottom if a workout exists
if workout_def:
    # Log YAML viewing (only once per session)
    if 'yaml_viewed' not in st.session_state:
        logger.log_event('yaml_viewed')
        st.session_state.yaml_viewed = True
    
    st.markdown("---")
    st.subheader("YAML Definition (Read-Only)")
    yaml_bottom = yaml.safe_dump(
        workout_def.model_dump(mode="json", exclude_none=True),
        sort_keys=False,
        indent=2,
    )
    st.code(yaml_bottom, language="yaml")
