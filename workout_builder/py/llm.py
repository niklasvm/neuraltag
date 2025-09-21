import shutil
import subprocess
from dotenv import load_dotenv
from pydantic_ai import Agent
import yaml
from workout_builder.py.workout_definition import WorkoutDefinition
from pathlib import Path
import re

load_dotenv(override=True)

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# # gemma-3-27b-it
# system_prompt = f"""
# You are a helpful assistant that helps translate user requests into structured workout definitions using the json schema:
# ```
# {schema}
# ```
# """

# agent = Agent(model="google-gla:gemma-3-27b-it")
# prompt = """
# Help me generate a yaml file for the workout: 15 min warmup + 8x[800m@3:30] + 15 min cool down
# """
# result = agent.run_sync(system_prompt + prompt)

# # gemma-3


def generate_workout(workout_description: str, model: str, use_structured_output: bool) -> WorkoutDefinition:
    schema = WorkoutDefinition.model_json_schema()
    
    system_prompt = """You are a helpful assistant that helps translate user requests into structured workout definitions.
    Also give the workout a creative name and description."""
    
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

        workout: WorkoutDefinition = WorkoutDefinition.model_validate_json(json_text)
    else:
        agent = Agent(model=model, system_prompt=system_prompt)
        prompt = f"""Help me generate a workout for: {workout_description}"""
        result = agent.run_sync(prompt,output_type=WorkoutDefinition)

        workout = result.output

    print(f"💡 Created workout: {workout.metadata.name}")
    return workout


def _sanitize_name(n: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 _-]", "", n)[:30]
    return cleaned.replace(" ", "_")


def encode_to_fit(yaml_file: str, fit_file: str):
    JAVA_DIR = Path(
        "/Users/niklasvonmaltzahn/Documents/personal/neuraltag/workout_builder/java"
    )
    JAVA_BUILD = JAVA_DIR / "build"
    JAVA_LIB_DIR = JAVA_DIR / "lib"
    FIT_JAR = JAVA_LIB_DIR / "fit.jar"
    SNAKEYAML_JAR = JAVA_LIB_DIR / "snakeyaml-2.2.jar"
    CLASSPATH = ":".join([str(JAVA_BUILD), str(FIT_JAR), str(SNAKEYAML_JAR)])
    ENCODER_CLASS = "com.neuraltag.workout.EncodeYamlWorkout"

    with open(yaml_file, "r") as yf:
        data = yaml.safe_load(yf)
    meta_name = data.get("metadata", {}).get("name", "Workout")
    produced_filename = f"{_sanitize_name(meta_name)}.fit"

    command = f"java -cp {CLASSPATH} {ENCODER_CLASS} {yaml_file}"
    subprocess.run(command, shell=True, check=True)
    shutil.move(produced_filename, fit_file)


logger.info("Starting workout generation")
input = "15 min warmup + 8x[800m@3:30] + 15 min cool down"

logger.info(f"Converting `{input}` to yaml")
workout = generate_workout(
    workout_description=input,
    # model="google-gla:gemma-3-27b-it",
    model = "google-gla:gemini-2.5-flash-lite",
    use_structured_output=True,
)

yaml_file = "/Users/niklasvonmaltzahn/Documents/personal/neuraltag/workout_builder/examples/llm_generated_workout.yaml"
fit_file = "/Users/niklasvonmaltzahn/Documents/personal/neuraltag/workout_builder/examples/llm_generated_workout.fit"
with open(yaml_file, "w") as f:
    yaml.dump(workout.model_dump(mode="json", exclude_none=True), f)


logger.info(f"Encoding {yaml_file} to {fit_file}")
encode_to_fit(yaml_file, fit_file)
logger.info(f"💾 Wrote workout to {yaml_file} and {fit_file}")
