import logging
from datetime import datetime
from typing import Optional

from pylegifrance.fonds.loda import Loda
from pylegifrance.models.generated.model import DatePeriod
from pylegifrance.models.loda.search import SearchRequest

from app.config import get_api_client
from app.services.dynamo_utils import DynamoDBClient

logger = logging.getLogger(__name__)


class LawSyncService:
    def __init__(self, dynamo_client: DynamoDBClient):
        self.dynamo_client = dynamo_client
        self.loda_api = Loda(get_api_client())

    def sync_laws_for_year(self, year: Optional[int] = None) -> int:
        """
        Synchronize laws from Legifrance for a given year based on publication date.

        Args:
            year: The year to sync laws for based on publication date. Defaults to current year.

        Returns:
            int: Number of new laws synced
        """
        if year is None:
            year = datetime.now().year

        logger.info("Synchronizing laws for year %d...", year)

        all_laws = []
        page_number = 1

        while True:
            search_request = SearchRequest(
                natures=["LOI", "DECRET", "ORDONNANCE"],
                page_number=page_number,
                page_size=10,
                date_publication=DatePeriod(
                    start=datetime(year, 1, 1), end=datetime(year, 12, 31)
                ),
            )

            laws = self.loda_api.search(search_request)

            if not laws:
                break

            all_laws.extend(laws)

            if len(laws) < 10:
                break

            page_number += 1

        # Sync laws to DynamoDB
        if all_laws:
            result = self.dynamo_client.sync_new_entries_to_dynamodb(all_laws)
            logger.info("Synchronization complete for %d. %s", year, result)
            return len(all_laws)
        else:
            logger.info("No laws found for year %d", year)
            return 0
