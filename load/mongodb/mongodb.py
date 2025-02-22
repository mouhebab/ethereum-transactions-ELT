from pymongo import MongoClient, UpdateOne
import logging
import pandas as pd
import numpy as np
from typing import Any, Dict, List,Tuple, Optional
import requests
import yaml
from helpers.utils import load_yaml_file,load_file,get_local_path
from pathlib import Path
from pymongo.errors import BulkWriteError


import json
from bson import BSON

def get_mongo_connection_config(db_configs: Dict) -> Tuple[str, str]:
    try:
        mongo = db_configs["Mongo"]["Mongo_Config"]
        return mongo["host_url"], mongo["db_name"]
    except KeyError as e:
        raise ValueError(f"Missing MongoDB config key: {e}")

def get_collection_config(db_configs: Dict, collection_key: str) -> Tuple[str, List[str]]:
    try:
        collection_cfg = db_configs["Mongo"]["Mongo_Collections"][collection_key]
        return collection_cfg["collection_name"], collection_cfg["primary_key"]
    except KeyError as e:
        raise ValueError(f"Missing collection config for key: {collection_key}") from e

    

def initialize_mongo_db(host:str, database_name:str)-> Tuple[MongoClient, Any]:
    try:
        client = MongoClient(host)
        db = client[database_name]
        return client,db
    except Exception as e:
        logging.error(f"Error in initiating Mongo client: {e}")    
    return None,None

def bulk_insert_mongodb(host: str, database_name: str, collection_name: str, data: List[Dict[str, Any]], 
                        unique_keys: Optional[List[str]] = None) -> None:

    client = MongoClient(host)
    db = client[database_name]
    collection = db[collection_name]

    if unique_keys:
        data = [
            {**doc, "_id": doc.get(unique_keys[0])} if len(unique_keys) == 1
            else {**doc, "_id": "_".join(str(doc.get(k)) for k in unique_keys)}
            for doc in data
        ]

    try:
        result = collection.insert_many(data, ordered=False)
        logging.info(f"[bulk_insert_mongodb] Inserted {len(result.inserted_ids)} documents.")
    except BulkWriteError as e:
        inserted = e.details.get("nInserted", 0)
        skipped = len(e.details.get("writeErrors", []))
        logging.warning(f"[bulk_insert_mongodb] Inserted {inserted}, skipped {skipped} duplicates.")
    except Exception as e:
        logging.error(f"[bulk_insert_mongodb] Unexpected error: {e}")
    finally:
        client.close()
        logging.debug("[bulk_insert_mongodb] MongoDB client closed.")

        

def load_to_mongo(data: List[Dict], collection_key: str) -> None:

    db_params_path = get_local_path(__file__,"params/mongodb_params.yaml")
    db_configs = load_yaml_file(__file__,db_params_path)

    host, db_name = get_mongo_connection_config(db_configs)
    collection_name, primary_keys = get_collection_config(db_configs, collection_key)

    bulk_insert_mongodb(host, db_name, collection_name, data, primary_keys)


def read_from_mongodb(host: str, db_name: str, collection_name: str) -> Optional[List[Dict]]:
    
    try:
        client, db = initialize_mongo_db(host, db_name)
        if client is None or db is None:
            logging.error("MongoDB: Failed to connect.")
            return None
        else:
            logging.debug("MongoDB: Connected successfully.")

        data = list(db[collection_name].find())
        logging.info(f"MongoDB: Loaded {len(data)} records from '{collection_name}'.")
        return data

    except Exception as e:
        logging.error(f"MongoDB: Error reading from collection '{collection_name}': {e}")
        return None

    finally:
        if 'client' in locals() and client:
            client.close()
            logging.debug("MongoDB: Client closed.")
            

def load_from_mongo(collection_key: str) -> Optional[List[Dict]]:
    db_params_path = get_local_path(__file__, "params/mongodb_params.yaml")
    db_configs = load_yaml_file(__file__, db_params_path)

    host, db_name = get_mongo_connection_config(db_configs)
    collection_name, _ = get_collection_config(db_configs, collection_key)

    return read_from_mongodb(host, db_name, collection_name)



