from __future__ import annotations


from pydantic import BaseModel
from src.database.models import PromptResponse

from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings
from pydantic_ai.models.google import GoogleModel


class NameResult(BaseModel):
    name: str
    description: str
    probability: float


def run_naming_agent(
    *, activity_id: int, rendered_prompt: str, temperature: float, llm_model: str
) -> tuple[PromptResponse, list[NameResult], str]:
    # ollama_model = OpenAIModel(
    #     model_name='deepseek-r1:latest', provider=OpenAIProvider(base_url='http://localhost:11434/v1')
    # )
    fallback_models = FallbackModel(
        # GoogleModel("gemini-2.5-pro"),
        GoogleModel("gemini-flash-latest"),
        GoogleModel("gemini-2.5-flash"),
        GoogleModel("gemini-2.0-flash"),
        GoogleModel("gemini-2.0-flash-lite")
    )
    naming_agent = Agent(
        fallback_models,
        instrument=True,
        retries=0,
        output_type=list[NameResult],
        model_settings=ModelSettings(
            temperature=temperature,
        ),
    )

    result = naming_agent.run_sync(
        rendered_prompt,
    )

    # if rendered_prompt is a list, take the first element (string, discard binary content)
    if isinstance(rendered_prompt, list):
        rendered_prompt = rendered_prompt[1]
    prompt_response = PromptResponse(
        activity_id=activity_id,
        prompt=rendered_prompt,
        response=str(result.output),
        llm_model=llm_model,
        temperature=temperature,
    )

    try:
        model_name = str(result.response.model_name)
    except Exception:
        model_name = "unknown"

    # parse response
    return prompt_response, result.output, model_name
