import json
from google import genai
import pandas as pd
from pydantic import BaseModel


class NameResult(BaseModel):
    name: str
    description: str
    probability: float


def generate_activity_name_with_gemini(
    activity_id: int, data: pd.DataFrame, number_of_options: int, api_key: str
) -> list[NameResult]:
    input = data[data["id"] == activity_id].iloc[0]
    context_data = data.drop(data[data["id"] == activity_id].index)

    del input["name"]
    del input["id"]
    del context_data["id"]

    # create context
    prompt = f"""
    [BEGIN CONTEXT]
    {context_data.to_string(index=False)}
    [END CONTEXT]

    [OUTPUT FORMAT]
    class Response(BaseModel):
        name: str
        description: str
        probability: float
    [END OUTPUT FORMAT]

    Given the following input:
    {input.to_string(index=True)}

    [PROMPT]
    Provide {number_of_options} options for a name for the input activity that is consistent with the data. The names can have one or more emojis. For each name, explain why it was chosen.
    """

    with open("prompt.txt", "w") as f:
        f.write(prompt)

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)

    # parse response
    formatted_results = "\n".join(response.text.strip().split("\n")[1:-1])
    results = json.loads(formatted_results)

    results = [NameResult(**result) for result in results]

    return results
