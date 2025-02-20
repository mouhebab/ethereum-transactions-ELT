from pathlib import Path
import yaml
import logging
from typing import Dict,List,Any,Type,Set
import json

def get_local_path(base_file: str, relative_path: str) -> Path:

    return Path(base_file).parent.joinpath(relative_path)

def load_yaml_file(base_file: str, relative_path: str) -> Dict:

    path = get_local_path(base_file, relative_path)

    if not path.exists():
        logging.error(f"YAML file not found: {path}")
        raise FileNotFoundError(path)

    with path.open("r") as f:
        return yaml.safe_load(f)
    

def load_file(base_file: str, relative_path: str) -> Dict:

    path = get_local_path(base_file, relative_path)

    if not path.exists():
        logging.error(f"file not found: {path}")
        raise FileNotFoundError(path)

    with path.open("r") as file:
        return file.read()
    
def load_json(file_path: str) -> dict:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"[load_json] Error loading JSON file: {e}")
        return {}