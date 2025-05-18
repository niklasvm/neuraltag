from pathlib import Path
import jinja2 as j2

PROMPT_V1 = j2.Template(
    (Path(__file__).parent / "prompt_v1.j2").read_text(), undefined=j2.StrictUndefined
)
