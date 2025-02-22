from extract.extract_swaps import main as extract_main
from load.mongodb.mongodb import load_to_mongo,load_from_mongo
import logging

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s — %(levelname)s — %(message)s",
        handlers=[
            logging.FileHandler("log/pipeline.log"),
            logging.StreamHandler()
        ]
    )


def main():

    setup_logging()
    logging.info("ETL Pipeline Started")
    RAW_DATA_COLLECTION_KEY = "transactions_routes_raw"
    try: 
        logging.info("Starting Extraction Step") 
        raw_data = extract_main()
        logging.info("Extraction Completed")
        logging.info("Starting Loading raw data")
        load_to_mongo(raw_data,RAW_DATA_COLLECTION_KEY)
        logging.info("loading Completed")
        
    except Exception as e:
        logging.exception(f"ETL Pipeline Failed: {e}")


if __name__ == "__main__":
    main()