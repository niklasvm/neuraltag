from pathlib import Path
from workout_builder.py.workout_definition import WorkoutDefinition
import json

outfile = Path(__file__).parent.parent / "schemas/workout_definition_schema.json"

schema = WorkoutDefinition.model_json_schema()

# write to json
with open(outfile, "w") as f:
    json.dump(schema, f, indent=2)