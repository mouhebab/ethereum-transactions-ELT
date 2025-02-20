import logging
import numpy as np
from io import StringIO
from typing import Any, Dict, List,Tuple
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json
from itertools import chain
from extract.params.block_number_swaps.block_number import get_start_block_number,update_start_block_number, create_table
from helpers.utils import get_local_path,load_file
from secrets_loader.secrets_loader import load_env,get_env_vars
from flipside import Flipside
from extract.flipside_api_handler import extract_flipsidecrypto_data


flipside_api_key = get_env_vars(['flipside_key'])[0]

   
def get_transactions_per_function(query:str,function_signature:str,api_key:str=flipside_api_key):
    try:
        block_number = get_start_block_number(function_signature)
        params = {'function_signature': function_signature,'block_number':block_number} 
        transaction_data = extract_flipsidecrypto_data(query, params, api_key=api_key)
        logging.info(f"[get_transactions_per_function] for {function_signature}) : {len(transaction_data)} rows Fetched")
        update_start_block_number(transaction_data,function_signature)
        return transaction_data
    except Exception as e:
        logging.error(f"[get_transactions_per_function] error: {e}")
        return []
    
def get_transactions(function_signatures:list,query:str) -> List:
    all_results = {}
    try:   
        with ThreadPoolExecutor() as executor:
            future_to_func_sig = {executor.submit(get_transactions_per_function, query,func_sig): func_sig for func_sig in function_signatures}
            for future in as_completed(future_to_func_sig):
                func_sig = future_to_func_sig[future]
                result = future.result()
                all_results[func_sig] = result
    except Exception as e:
        logging.error(f"[get_transactions] error in  fetching  transactions: {e}")

    flattened_values = list(chain.from_iterable(all_results.values()))
    logging.info(f"[get_transactions] total of : {len(flattened_values)} rows Fetched")       
    return flattened_values

def main():
    query_path = get_local_path(__file__,"params/queries/query_router_tx.sql")
    function_signatures = ['0xf28c0498'] #'0xc04b8d59',
    create_table()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    get_tx_query = load_file(__file__,query_path)
    transactions_data = get_transactions(function_signatures,get_tx_query)
    
    return transactions_data
 
if __name__ == "__main__":
    main()