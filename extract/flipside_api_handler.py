import requests
import time
import logging
from typing import Any, Dict, List, Optional
from enum import Enum
from flipside import Flipside


class QueryState(Enum):
    SUCCESS = "QUERY_STATE_SUCCESS"
    FAILED = "QUERY_STATE_FAILED"
    CANCELED = "QUERY_STATE_CANCELED"
    STREAMING_RESULTS = "QUERY_STATE_STREAMING_RESULTS"
    RUNNING = "QUERY_STATE_RUNNING"
    READY = "QUERY_STATE_READY"

SUCCESS_STATE = QueryState.SUCCESS.value
FAILURE_STATES = {QueryState.FAILED.value, QueryState.CANCELED.value}
PENDING_STATES = {
    QueryState.STREAMING_RESULTS.value,
    QueryState.RUNNING.value,
    QueryState.READY.value,
}



FLIPSIDE_API_URL = "https://api-v2.flipsidecrypto.xyz/json-rpc"
FLIPSIDE_INSTANCE_URL = "https://api-v2.flipsidecrypto.xyz"
HEADERS_TEMPLATE = {
    "Content-Type": "application/json"
}



def build_headers(api_key: str) -> Dict[str, str]:
    return {**HEADERS_TEMPLATE, "x-api-key": api_key}


def format_query(query: str, params: Dict[str, Any]) -> str:
    try:
        return query.format(**params)
    except Exception as e:
        raise ValueError(f"[format_query] Error formatting query: {e}")



def create_query_run(query: str, api_key: str) -> Optional[str]:
    headers = build_headers(api_key)

    payload = {
        "jsonrpc": "2.0",
        "method": "createQueryRun",
        "params": [{
            "resultTTLHours": 1,
            "maxAgeMinutes": 0,
            "sql": query,
            "tags": {"source": "postman-demo", "env": "test"},
            "dataSource": "snowflake-default",
            "dataProvider": "flipside"
        }],
        "id": 1
    }

    try:
        response = requests.post(FLIPSIDE_API_URL, json=payload, headers=headers)
        response.raise_for_status()

        if response.status_code == 200:
            logging.info("Query run created successfully.")
            logging.debug(response.json())
            return response.json()['result']['queryRequest']['queryRunId']
        else:
            raise requests.exceptions.HTTPError(
                f"Unexpected status code: {response.status_code}. Details: {response.text}"
            )
    except Exception as e:
        logging.error(f"[create_query_run] Error: {e}")
        return None


def get_query_state(query_run_id: str, api_key: str) -> Optional[str]:
    headers = build_headers(api_key)

    payload = {
        "jsonrpc": "2.0",
        "method": "getQueryRun",
        "params": [{"queryRunId": query_run_id}],
        "id": 1
    }

    try:
        response = requests.post(FLIPSIDE_API_URL, json=payload, headers=headers)
        response.raise_for_status()

        state = response.json()['result']['queryRun']['state']
        logging.debug(f"[get_query_state] State: {state}")
        return state
    except Exception as e:
        logging.error(f"[get_query_state] Error: {e}")
        return None


def query_result_pagination(query_run_id: str, api_key: str, page_size: int = 70000) -> Optional[List[Dict[str, Any]]]:
    flipside = Flipside(api_key, FLIPSIDE_INSTANCE_URL)
    current_page = 1
    total_pages = 3
    all_rows = []

    while current_page <= total_pages:
        try:
            result = flipside.get_query_results(query_run_id, page_number=current_page, page_size=page_size)

            if result.records:
                total_pages = result.page.totalPages
                all_rows.extend(result.records)
                logging.debug(f"[Pagination] Page {current_page}/{total_pages}, Rows: {len(result.records)}")
            else:
                logging.warning("[Pagination] No records found.")
                break

        except Exception as e:
            logging.error(f"[Pagination] Error: {e}")
            return None

        current_page += 1

    logging.info(f"[Pagination] Retrieved {len(all_rows)} rows across {total_pages} pages.")
    return all_rows



# main flipside extract


def extract_flipsidecrypto_data(
    query: str,
    params: Dict,
    api_key: str,
    retry_time: int = 90,
    timeout: int = 600,
    query_run_id: str = None
) -> Optional[List[Dict[str, Any]]]:
    try:
        if not query_run_id:
            logging.info(f"[extract_flipsidecrypto_data] Starting query with params: {params}")
            formatted_query = format_query(query, params)
            query_run_id = create_query_run(formatted_query, api_key)

            if not query_run_id:
                raise RuntimeError("QueryRunId could not be generated.")

        
        state = None
        start_time = time.time()

        while state != SUCCESS_STATE:
            state = get_query_state(query_run_id, api_key)

            if state == SUCCESS_STATE:
                break
            elif state in FAILURE_STATES:
                raise RuntimeError(f"Query execution failed or was canceled. State: {state}")
            elif state in PENDING_STATES:
                if time.time() - start_time > timeout:
                    raise TimeoutError("Query execution exceeded timeout limit.")

                logging.info("Waiting for query execution...")
                logging.debug(f"Retrying in {retry_time} seconds.")
                time.sleep(retry_time)
            else:
                raise ValueError(f"Unexpected query state: {state}")

        return query_result_pagination(query_run_id, api_key)

    except TimeoutError as e:
        logging.error(f"[extract_flipsidecrypto_data] Timeout Error: {e}")
    except RuntimeError as e:
        logging.error(f"[extract_flipsidecrypto_data] Runtime Error: {e}")
    except Exception as e:
        logging.error(f"[extract_flipsidecrypto_data] General Error: {e}")

    return None