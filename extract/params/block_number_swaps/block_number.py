from typing import Any, List,Tuple
import logging
import sqlite3
from helpers.utils import get_local_path



DEFAULT_BLOCK_NUMBER_DB_PATH = get_local_path(__file__,'block_number.db')

def get_db_connection(DB_FILE:str= DEFAULT_BLOCK_NUMBER_DB_PATH):
    conn = sqlite3.connect(DB_FILE)
    return conn

# Function to create the table if it doesn't exist
def create_table(file_path:str = DEFAULT_BLOCK_NUMBER_DB_PATH):
    conn = None
    try:
        conn = get_db_connection(file_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS block_numbers (
                function_signature TEXT PRIMARY KEY, 
                block_number INTEGER
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"[create_table] Error creating table: {e}")
    finally:
        if conn is not None:
            conn.close()
            logging.debug("[create_table] SQLite connection closed.")

# Function to get the start block number from the database
def get_start_block_number(function_signature: str, file_path: str = DEFAULT_BLOCK_NUMBER_DB_PATH, default: int = 0) -> int:
    try:
        conn = get_db_connection(file_path)
        cursor = conn.cursor()
        cursor.execute("SELECT block_number FROM block_numbers WHERE function_signature = ?", (function_signature,))
        result = cursor.fetchone()

        if result:
            return result[0]
        else:
            logging.warning(f"[get_start_block_number] function_signature '{function_signature}' not found. Returning default value: {default}")
            return default
    except sqlite3.Error as e:
        logging.error(f"[get_start_block_number] Error reading block number for function_signature '{function_signature}': {e}")
        return default
    finally:
        conn.close()

# Function to update the block numbers in the database
def update_start_block_number(data: List, function_signature:str,file_path: str=DEFAULT_BLOCK_NUMBER_DB_PATH) -> None:
    try:
        conn = get_db_connection(file_path)
        cursor = conn.cursor()       
        if data:
            last_block_number = max(event['block_number'] for event in data)
            cursor.execute("""
                INSERT OR REPLACE INTO block_numbers (function_signature, block_number) 
                VALUES (?, ?)
            """, (function_signature, last_block_number))
            logging.debug(f" [update_start_block_number] Block number for function_signature {function_signature} updated to {last_block_number}")
        else:
            logging.warning(f"[update_start_block_number] No events found for function_signature {function_signature}, skipping.")

        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"[update_start_block_number] Error updating block numbers: {e}")
    finally:
        conn.close()
