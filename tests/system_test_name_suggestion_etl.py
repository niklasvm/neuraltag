from pprint import pp
from src.app.config import settings
from src.database.adapter import Database

if __name__ == "__main__":
    # name_suggestion_etl = NameSuggestionETL(
    #     settings=settings,
    #     # llm_model="google-gla:gemini-2.5-pro-exp-03-25",
    #     llm_model="google-gla:gemini-2.0-flash",
    #     activity_id=14069608165,
    #     days=365,
    #     temperature=2,
    #     number_of_options=10,
    # )

    # name_suggestion_etl.run()

    # get results
    db = Database(
        settings.postgres_connection_string,
        encryption_key=settings.encryption_key,
    )
    name_suggestions = db.get_name_suggestions_by_activity_id(
        activity_id=14069608165,
    )
    pp(name_suggestions)
