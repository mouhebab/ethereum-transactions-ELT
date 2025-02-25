import logging
import os
import sys
import json
import requests
import pandas as pd
from typing import Any, List, Tuple, Dict, Optional
from concurrent.futures import ThreadPoolExecutor,as_completed
from web3 import Web3
from web3.contract import Contract
from secrets_loader.secrets_loader import get_env_vars
from bson.decimal128 import Decimal128
from decimal import Decimal

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(levelname)s — %(message)s")


def fetch_contract_abi(contract_address: str, api_key: str) -> Dict[str, Any]:
    url = "https://api.etherscan.io/v2/api"
    params = {
        "chainid": 1,
        "module": "contract",
        "action": "getabi",
        "address": contract_address,
        "apikey": api_key
    }

    try:
        response = requests.get(url, params=params)
        return json.loads(response.json()['result'])
    except Exception as e:
        logging.error(f"[fetch_contract_abi] Request error: {e}")
        return {}


def initialize_contract_instance(contract_address: str, api_key: str) -> Contract:
    try:
        web3 = Web3()
        abi = fetch_contract_abi(contract_address, api_key)
        logging.debug(f"Contract ABI: {abi}")
        contract_instance = web3.eth.contract(abi=abi)
        logging.debug(f"Contract instance: {contract_instance}")
        logging.info("Contract instance created successfully.")
        return contract_instance
    except Exception as e:
        logging.error(f"[initialize_contract_instance] Error: {e}")
        raise


def decode_path(path_bytes: bytes) -> Tuple[List[str], List[Dict[str, Any]]]:
    hex_str = path_bytes.hex()
    tokens = []
    fees = []

    i = 0
    if len(hex_str) < 40:
        return [], []

    token_in = "0x" + hex_str[i:i+40]
    tokens.append(token_in)
    i += 40

    while i + 6 + 40 <= len(hex_str):
        fee_hex = hex_str[i:i+6]
        fee = int(fee_hex, 16)
        i += 6

        token_out = "0x" + hex_str[i:i+40]
        tokens.append(token_out) 
        i += 40

        fees.append(fee)

    return tokens, fees



def decode_func_input_data(input_data_raw: str, contract_instance: Contract) -> Optional[Dict[str, Any]]:
    try:
        func, decoded_input = contract_instance.decode_function_input(input_data_raw)

        if "params" not in decoded_input or not isinstance(decoded_input["params"], dict):
            return None

        params = decoded_input["params"]

        if "path" in params and isinstance(params["path"], bytes):
            tokens, fees = decode_path(params["path"])

            
            params["path_tokens"] = tokens
            params["path_fees"] = fees
            params["path"] = "0x" + params["path"].hex()

        
        params["function_name"] = func.fn_name

        return params

    except Exception as e:
        logging.warning(f"[decode_input_data] Failed to decode input: {e}")
        return None


def parallelize_transaction_input_decoding(inputs: List[str], contract_instance: Contract, max_workers: int = 8) -> List[Optional[Dict[str, Any]]]:
    def safe_decode(idx_and_input):
        idx, input_data = idx_and_input
        return idx, decode_func_input_data(input_data, contract_instance)

    results = [None] * len(inputs)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(safe_decode, (idx, input_data)) for idx, input_data in enumerate(inputs)]
        for future in as_completed(futures):
            try:
                idx, result = future.result()
                results[idx] = result
            except Exception as e:
                logging.warning(f"[parallelize_decoding] Decode failed: {e}")

    return results




def decode_transactions_input(df: pd.DataFrame, contract_address: str, api_key: str, max_workers: int = 8) -> pd.DataFrame:
    try:
        contract_instance = initialize_contract_instance(contract_address, api_key)
        inputs = df["input_data"].values.tolist()
        decoded_inputs = parallelize_transaction_input_decoding(inputs, contract_instance, max_workers=max_workers)
        decoded_df = df[["_id","block_timestamp","block_number","tx_position","origin_function_signature"]].copy()
        decoded_df["decoded_input"] = decoded_inputs
        return decoded_df
         
    except Exception as e:
        logging.warning(f"[decode_transactions_input] Failed to decode input: {e}")
        return None
    

def decode_input_data_main(raw_data: pd.DataFrame)->List[Dict[str,Any]]:
    etherscan_api_key = get_env_vars(['etherscan_key'])[0]
    CONTRACT_ADDRESS = '0xe592427a0aece92de3edee1f18e0157c05861564'

    raw_df = pd.DataFrame(raw_data)

    if raw_df.empty:
        logging.warning("No data loaded from MongoDB.")
        return []

    logging.info(f"Loaded {len(raw_df)} rows from MongoDB.")
    decoded_df = decode_transactions_input(raw_df, contract_address=CONTRACT_ADDRESS, api_key=etherscan_api_key, max_workers=8)
    if decoded_df is None or decoded_df.empty:
        logging.warning("Decoded DataFrame is empty.")
        return []
    logging.debug("[decode_transactions_input]: %s", decoded_df.head(2))

    logging.info("Transactions are decoded successfully.")
    decoded_data = decoded_df.to_dict(orient="records")
    return decoded_data
