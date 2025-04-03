from math import fabs
import os
from b2sdk.v2 import InMemoryAccountInfo, B2Api, AuthInfoCache, Bucket
from b2sdk._internal.exception import FileNotPresent, B2Error, InvalidAuthToken

from downloads import DOWNLOADS_DIRECTORY
from loglib import logger


def connect_to_backblaze(account_id, app_key) -> B2Api:
    try:
        info = InMemoryAccountInfo()
        b2_api = B2Api(info, cache=AuthInfoCache(info))
        b2_api.authorize_account("production", account_id, app_key)
        return b2_api
    except InvalidAuthToken as e:
        logger.error("Invalid credentials provided.")
        raise e
    except B2Error as e:
        logger.error(f"Unable to connect to Backblaze.")
        raise e


def check_if_file_exists(bucket: Bucket, filename: str) -> bool:
    try:
        bucket.get_file_info_by_name(filename)
        return True
    except FileNotPresent:
        return False


def upload_files(bucket: Bucket, fpath: str):
    bucket.upload_local_file(
        local_file=fpath,
        file_name=fpath,
    )


def upload_files(dirname: str):
    account_id = os.getenv("BACKBLAZE_S3_KEY_ID")
    application_key = os.getenv("BACKBLAZE_S3_APP_KEY")
    bucket_name = os.getenv("BACKBLAZE_BUCKET_NAME")

    logger.debug(f"api key {application_key}")

    try:
        b2_api = connect_to_backblaze(account_id, application_key)
        bucket = b2_api.get_bucket_by_name(bucket_name)

        for filename in os.listdir(dirname):
            fpath = os.path.join(dirname, filename)
            # checking if it is a file
            if not os.path.isfile(fpath):
                continue
            logger.debug("local file %s", fpath)

            if check_if_file_exists(bucket, filename):
                logger.info("skipping file %s, already exists", filename)
                continue

            logger.info("uploading file %s", fpath)
            try:
                bucket.upload_local_file(
                    local_file=fpath,
                    file_name=filename,
                )
                logger.info("successfully uploaded file %s", fpath)
            except B2Error as e:
                logger.exception(f"could not upload file: {e}")

    except B2Error as e:
        logger.error(f"A backblaze error occurred: {e}")
        raise e

    except OSError as e:
        logger.error(f"An OS error occured: {e}")
        raise e


if __name__ == "__main__":
    logger.debug("debugging backblaze upload only")
    upload_files(DOWNLOADS_DIRECTORY)
