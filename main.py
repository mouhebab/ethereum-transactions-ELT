from extract.extract_swaps import main as extract_main
from load.mongodb.mongodb import load_to_mongo,load_from_mongo
from transform.decode_input_data import decode_input_data_main
from transform.process_decoded_input_data import process_decoded_input_main
from helpers.utils import prepare_for_mongo
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
    DECODED_DATA_COLLECTION_KEY = "transactions_routes_decoded"
    try: 
        logging.info("Starting Extraction Step") 
        raw_data = extract_main()
        logging.info("Extraction Completed")
        logging.info("Starting Loading raw data")
        load_to_mongo(raw_data,RAW_DATA_COLLECTION_KEY)
        logging.info("loading Completed")
        raw_data = load_from_mongo(collection_key=RAW_DATA_COLLECTION_KEY)
        logging.info("Start Decoding")
        decoded_data = decode_input_data_main(raw_data)
        decoded_data_processed = process_decoded_input_main(decoded_data)
        logging.info("Decoding & processing Completed")
        logging.info("Starting Loading decoded data")
        load_to_mongo(prepare_for_mongo(decoded_data_processed), DECODED_DATA_COLLECTION_KEY)
        logging.info("loading Completed")
    except Exception as e:
        logging.exception(f"ETL Pipeline Failed: {e}")


if __name__ == "__main__":
    main()