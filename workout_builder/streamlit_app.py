import tempfile
import shutil
from pathlib import Path
import yaml
import streamlit as st
import pandas as pd
import re
from workout_builder.py.workout_definition import WorkoutDefinition
from pydantic_ai import Agent
from dotenv import load_dotenv

load_dotenv(override=True)

# ---------------- Helper logic (inlined from notebook) ---------------- #

def _sanitize_name(n: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 _-]", "", n)[:30]
    return cleaned.replace(" ", "_")

def generate_workout(workout_description: str, model: str = "google-gla:gemini-2.5-flash-lite", use_structured_output: bool=False) -> WorkoutDefinition:
    schema = WorkoutDefinition.model_json_schema()
    
    system_prompt = """You are a helpful assistant that helps translate user requests into structured workout definitions.
    Provide the workout a creative name and description. Steps should also be creatively named with appropriate descriptions and notes"""
    
    if not use_structured_output:
        system_prompt = f"""
        {system_prompt}.
        Use the json schema for the output:
        ```
        {schema}
        ```
        
        """
        agent = Agent(model=model)
        prompt = f"""Help me generate a json file for the workout: {workout_description}"""
        result = agent.run_sync(system_prompt + prompt)

        # extract text between markdown code blocks
        match = re.search(r"```(json)?\n(.*?)\n```", result.output, re.DOTALL)
        if match:
            json_text = match.group(2)
            result.output = json_text
        else:
            print("No code block found")

        try:
            workout: WorkoutDefinition = WorkoutDefinition.model_validate_json(json_text)
        except:
            print("Failed to parse JSON, falling back to structured output")
            print(json_text)
    else:
        agent = Agent(model=model, system_prompt=system_prompt)
        prompt = f"""Help me generate a workout for: {workout_description}"""
        result = agent.run_sync(prompt,output_type=WorkoutDefinition)

        workout = result.output

    print(f"💡 Created workout: {workout.metadata.name}")
    return workout

def encode_to_fit(yaml_file: str, fit_file: str):
    """Encode a YAML workout to FIT using Java encoder without passing an explicit name.
    NOTE: This assumes the Java build & jars are already present."""
    JAVA_DIR = Path("/Users/niklasvonmaltzahn/Documents/personal/neuraltag/workout_builder/java")
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
    subprocess.run(f"java -cp {CLASSPATH} {ENCODER_CLASS} {yaml_file}", shell=True, check=True)
    shutil.move(produced_filename, fit_file)

st.set_page_config(page_title="Workout Builder", layout="wide")

st.title("🏃 Workout Builder & FIT Generator")

# Simplified UI (no advanced model/HR/structured controls)
st.caption("Enter a description. The app uses a fixed model and settings under the hood.")

prompt = st.text_area(
    "Workout Prompt",
    height=200,
    placeholder="Describe the workout (e.g. 10min warmup, 6x1km @4:00-4:05/km w/90s rest, 10min cooldown)"
)

generate_btn = st.button("Generate Workout", type="primary")

if "workout_def" not in st.session_state:
    st.session_state.workout_def = None
if "fit_bytes" not in st.session_state:
    st.session_state.fit_bytes = None
if "fit_filename" not in st.session_state:
    st.session_state.fit_filename = None

if generate_btn:
    if not prompt.strip():
        st.warning("Please enter a workout prompt first.")
    else:
        with st.spinner("Generating workout..."):
            try:
                workout_def = generate_workout(prompt)
                st.session_state.workout_def = workout_def
                tmp_dir = Path(tempfile.mkdtemp(prefix="workout_fit_"))
                yaml_path = tmp_dir / "workout.yaml"
                fit_path = tmp_dir / "workout.fit"
                yaml_text_local = yaml.safe_dump(workout_def.model_dump(mode="json", exclude_none=True), sort_keys=False, indent=2)
                with open(yaml_path, 'w') as f:
                    f.write(yaml_text_local)
                try:
                    encode_to_fit(str(yaml_path), str(fit_path))
                    st.session_state.fit_bytes = fit_path.read_bytes()
                    st.session_state.fit_filename = f"{_sanitize_name(workout_def.metadata.name)}.fit"
                finally:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception as e:
                st.error(f"Generation failed: {e}")

workout_def = st.session_state.workout_def

if workout_def:
    st.success(f"Generated: {workout_def.metadata.name}")

    # Download button directly under generation controls
    if st.session_state.fit_bytes:
        st.download_button(
            "Download FIT File",
            data=st.session_state.fit_bytes,
            file_name=st.session_state.fit_filename or "workout.fit",
            mime="application/octet-stream"
        )
    else:
        st.warning("FIT file not available.")

    # Expanded steps full width first
    def expand_to_df(w: WorkoutDefinition) -> pd.DataFrame:
        rows = []
        for step in w.expand():
            d = step.get('duration', {})
            t = step.get('target', {})
            dur_type = d.get('type')
            if dur_type == 'time':
                secs = d['time_ms']/1000
                dur_display = f"{secs:.0f}s"
            elif dur_type == 'distance':
                km = d['distance_cm']/100/1000
                dur_display = f"{km:.2f} km"
            elif dur_type == 'calories':
                dur_display = f"{d['calories']} cal"
            elif dur_type == 'hr_greater_than':
                dur_display = f"HR > {d['bpm']}"
            elif dur_type == 'hr_less_than':
                dur_display = f"HR < {d['bpm']}"
            else:
                dur_display = dur_type
            target_kind = t.get('kind') or t.get('zone')
            if target_kind in ('pace','pace_range'):
                low = t.get('low')
                high = t.get('high')
                def speed_to_pace(s):
                    if not s:
                        return None
                    mps = s/1000.0
                    if mps == 0:
                        return None
                    sec_per_km = 1000.0/mps
                    mins = int(sec_per_km//60)
                    secs = int(round(sec_per_km%60))
                    return f"{mins}:{secs:02d}"
                if target_kind == 'pace':
                    tgt_display = speed_to_pace(low)
                else:
                    tgt_display = f"{speed_to_pace(low)} - {speed_to_pace(high)}"
            elif target_kind in ('hr_range','cadence_range','power_range'):
                tgt_display = f"{t.get('low')}-{t.get('high')}"
            elif target_kind == 'hr_zone':
                tgt_display = f"Zone {t.get('zone')}"
            elif target_kind == 'power_zone':
                tgt_display = f"Power Z{t.get('zone')}"
            elif target_kind == 'open' or target_kind is None:
                tgt_display = 'Open'
            else:
                tgt_display = target_kind
            rows.append({
                'index': step['index'],
                'name': step.get('name'),
                'kind': step.get('kind'),
                'intensity': step.get('intensity'),
                'duration_type': dur_type,
                'duration': dur_display,
                'target': tgt_display,
                'note': step.get('note')
            })
        return pd.DataFrame(rows)

    st.subheader("Expanded Steps")
    st.dataframe(expand_to_df(workout_def), use_container_width=True)

    # YAML removed per simplified UI request
else:
    st.info("Enter a prompt and click 'Generate Workout' to begin.")

st.markdown("---")
with st.expander("How to Use & Device Transfer"):
    st.markdown(
        """
        ### 1. Run the App
        Launch the app (already packaged for you). No other CLI interaction is required.

        ### 2. Generate a Workout
        1. Enter a natural language prompt (e.g. *10min warmup, 6x1km @4:00-4:05/km w/90s rest, 10min cooldown*).
        2. Click **Generate Workout**.
        3. Review the Expanded Steps table (repeat groups are expanded here for clarity).
        4. Download the FIT file via the **Download FIT File** button.

        ### 3. Regenerating / Iterating
        - Change the prompt and click **Generate Workout** again; the previous result is replaced.
        - There is no manual YAML editing in this simplified mode; everything is handled internally.

        ### 4. Optional: Validate FIT File
        The Garmin `FitTestTool` often flags structured workouts with informational messages that are safe to ignore, but you can still inspect or decode:
        ```bash
        # Decode to CSV
        java -jar workout_builder/java/lib/FitCSVTool.jar -b Your_Workout.fit

        # (Optional) Run test tool (may produce non-fatal warnings)
        java -jar workout_builder/java/lib/FitTestTool.jar Your_Workout.fit
        ```
        Inspect the CSV for step ordering, duration types, targets, and repeat controller steps.

        ### 5. Copy FIT to Your Garmin Device (USB)
        1. Connect device via USB; it mounts like a drive (on macOS usually under `/Volumes/GARMIN`).
        2. Prefer target directory (device dependent):
           - `GARMIN/Workouts/` (many devices auto-import on unplug)
           - or `GARMIN/NEWFILES/` (device will move & ingest next boot)
        3. Copy the downloaded `.fit` file into one of those directories.
        4. Properly eject the volume.
        5. On the watch, open the Workouts / Training menu; your custom workout should appear under the given name.

        If the workout does not appear:
        - Ensure file extension is `.fit` (not duplicated like `.fit.fit`).
        - Remove special characters from the name (this app already sanitizes to alphanumeric + `_` / `-`).
        - Reboot the device.

    ### 6. Heart Rate Handling
    Heart rate threshold semantics are handled automatically. No manual offset configuration is exposed in this interface.

        ### 7. Troubleshooting
        | Issue | Suggestion |
        |-------|-----------|
        | FIT download button missing | Generation may have failed—check error message above. |
        | Device ignores file | Try placing into `NEWFILES`; verify file size > 0; decode with FitCSVTool to confirm validity. |
        | Pace ranges look odd | Remember internal representation is speed (m/s * 1000). Display here converts back to min/km. |
        | Repeats compressed on device | That is expected—device shows controller repeat, while the table here shows expanded steps. |

        ### 8. Advanced CLI (Disabled in Simplified Mode)
        Direct YAML editing & re-encoding are not part of this streamlined interface. Use the full developer version if you need that workflow.
        """
    )
with st.expander("Notes & Tips"):
    st.markdown(
        "- Optional targets/durations omitted become open.\n"
        "- Distance step durations are internally centimeters (FIT uses cm).\n"
        "- Pace conversion uses scaled speed integers (m/s * 1000).\n"
        "- Repeat groups appear as controller steps unless expanded."
    )
