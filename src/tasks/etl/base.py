from abc import ABC, abstractmethod
from src.app.config import Settings
from src.database.adapter import Database


class ETL(ABC):
    def __init__(self, settings: Settings):
        self.settings = settings

        self.db = Database(
            connection_string=settings.postgres_connection_string,
            encryption_key=settings.encryption_key,
        )

    def extract(self):
        """Extract data from the source."""

    def transform(self):
        """Transform data"""

    @abstractmethod
    def load(self):
        """Load data into the target."""

    def run(self):
        """Run the ETL process."""
        self.extract()
        self.transform()
        return self.load()
