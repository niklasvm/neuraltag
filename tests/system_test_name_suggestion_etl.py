from src.app.config import settings
from src.tasks.etl import NameSuggestionETL

if __name__ == "__main__":
    name_suggestion_etl = NameSuggestionETL(
        settings=settings,
        # llm_model="google-gla:gemini-2.5-pro-exp-03-25",
        llm_model="google-gla:gemini-2.0-flash",
        activity_id=14069608165,
        days=365,
        temperature=1,
        number_of_options=10,
    )

    name_suggestion_etl.run()
