import logging
import pandas as pd
from typing import Any, List, Tuple, Dict, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(levelname)s — %(message)s")


def process_exactinput_func(decoded: Dict[str, Any]) -> Tuple[str, List[str], List[int], int, str]:

    path = decoded.get("path")
    tokens = decoded.get("path_tokens", [])
    fees = [int(fee) for fee in decoded.get("path_fees", [])]

    value = int(decoded.get("amountIn", 0))
    value_in_token = tokens[0] if tokens else None

    return path, tokens, fees, value, value_in_token

def process_exactoutput_func(decoded: Dict[str, Any]) -> Tuple[str, List[str], List[int], int, str]:

    path = decoded.get("path")
    tokens = decoded.get("path_tokens", [])[::-1]
    fees = [int(fee) for fee in decoded.get("path_fees", [])[::-1]]

    value = int(decoded.get("amountOut", 0))
    value_in_token = tokens[0] if tokens else None

    return path, tokens, fees, value, value_in_token

def extract_pairs_and_edge(tokens: List[str], fees: List[int]) -> Dict[str, Any]:
    
    path_pairs = []
    for i in range(len(tokens) - 1):
        path_pairs.append({
            "tokenIn": tokens[i],
            "tokenOut": tokens[i + 1],
            "fee": fees[i]
        })

    edge_tokens = {
        "tokenIn": tokens[0],
        "tokenOut": tokens[-1]
    }

    return {
        "path_pairs": path_pairs,
        "edge_tokens": edge_tokens
    }

def process_decoded_input(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:

    decoded = data.get("decoded_input", {})
    if not decoded:
        return None

    func_sig = data.get("origin_function_signature", "").lower()

    if func_sig == "0xc04b8d59":  # exactInput
        path, tokens, fees, value, value_in_token = process_exactinput_func(decoded)

    elif func_sig == "0xf28c0498":  # exactOutput
        path, tokens, fees, value, value_in_token = process_exactoutput_func(decoded)

    else:
        logging.warning(f"[process_decoded_input] Unknown function signature: {func_sig}")
        return None

    # Metadata from raw document
    processed_input = {
        "_id": data.get("_id"),
        "block_timestamp": data.get("block_timestamp"),
        "block_number": data.get("block_number"),
        "tx_position": data.get("tx_position"),
        "origin_function_signature": data.get("origin_function_signature")
    }

    # Selected fields from decoded_input
    decoded_fields = {
        "function_name": decoded.get("function_name"),
        "recipient": decoded.get("recipient"),
        "deadline": decoded.get("deadline"),
        "path": path,
        "path_tokens": tokens,
        "path_fees": fees,
        "value": value,
        "value_in_token": value_in_token
    }

    # Extract path_pairs and edge_tokens
    pairs_and_edge = extract_pairs_and_edge(tokens, fees)
    decoded_fields.update(pairs_and_edge)

    
    processed_input.update(decoded_fields)
    return processed_input


def process_decoded_input_main(decoded_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:

    processed_data = []

    for doc in decoded_data:
        try:
            processed = process_decoded_input(doc)
            if processed is not None:
                processed_data.append(processed)
        except Exception as e:
            logging.warning(f"[process_decoded_input_main] Failed processing doc with _id {doc.get('_id', 'unknown')}: {e}")
            continue

    return processed_data


