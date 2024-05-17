from kaggle import KaggleApi, ApiClient
from kaggle.configuration import Configuration
from pprint import pprint
import os

os.environ["KAGGLE_CONFIG_DIR"] = os.getcwd()

config = Configuration()

api_instance = KaggleApi(ApiClient(config))
owner_slug = "arashnic"
dataset_slug = "book-recommendation-dataset"

# Download dataset file
# api_response = api_instance.datasets_download_file(owner_slug, dataset_slug, file_name)
api_response = api_instance.datasets_download(owner_slug, dataset_slug)
