import time
import logging
from http_client import query   # import the function from previous task

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.DEBUG,
)

# Elasticsearch configuration
ROOT_URL = "http://134.169.115.91:32200/"
INDEX = "assignment3_index"
DOC_TYPE = "test_sensor"

# 1) INDEX FIVE ENTRIES (POST)
logging.info("Indexing five entries")

for i in range(1, 6):
    query(
        url=f"{ROOT_URL}{INDEX}/{DOC_TYPE}/{i}",
        method="POST",
        payload={
            "id": f"sensor_{i}",
            "temperature": 20 + i
        }
    )
    time.sleep(0.2)

# 2) UPDATE ALL ENTRIES (PUT)
logging.info("Updating temperature values")

for i in range(1, 6):
    query(
        url=f"{ROOT_URL}{INDEX}/{DOC_TYPE}/{i}",
        method="PUT",
        payload={
            "id": f"sensor_{i}",
            "temperature": 30 + i
        }
    )
    time.sleep(0.2)

# 3) QUERY INDEX TO VERIFY MODIFICATIONS (GET)
logging.info("Querying index to verify updates")

query(
    url=f"{ROOT_URL}{INDEX}/_search",
    method="GET"
)

# 4) DELETE ALL ENTRIES (DELETE INDEX)
logging.info("Deleting index and all entries")

query(
    url=f"{ROOT_URL}{INDEX}",
    method="DELETE"
)
