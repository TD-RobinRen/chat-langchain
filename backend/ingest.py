"""Load html from files, clean up, split, ingest into Weaviate."""
import logging
import os
from dotenv import load_dotenv

import weaviate
from langchain.indexes import SQLRecordManager, index
from langchain_community.vectorstores import Weaviate
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.document_loaders import JSONLoader
from pprint import pprint

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

while_list = ['name', 'version', 'default_exits']

def metadata_func(record: dict, metadata: dict) -> dict:
    metadata["component_name"] = record.get("name")
    metadata["component_version"] = record.get("version")
    metadata["source"] = record.get("source")
    return metadata

def load_components_folder():
    loader = DirectoryLoader(
        './studio_components',
        glob="**/*.json",
        loader_cls=JSONLoader,
        loader_kwargs={'jq_schema': '.', 'metadata_func': metadata_func, 'text_content': False},
        show_progress=True)
    return loader.load()

def load_components_description():
    file_path='./schema/components_descriptions.json'
    loader = JSONLoader(
        file_path=file_path,
        jq_schema='.[]',
        metadata_func= metadata_func,
        text_content=False)

    return loader.load()

def get_embeddings_model() -> Embeddings:
    return OpenAIEmbeddings(model="text-embedding-3-small", chunk_size=200)

def ingest_docs():
    WEAVIATE_URL = os.environ["WEAVIATE_URL"]
    WEAVIATE_API_KEY = os.environ["WEAVIATE_API_KEY"]
    WEAVIATE_INDEX_NAME = os.environ["WEAVIATE_INDEX_NAME"]
    DATABASE_HOST = os.environ["DATABASE_HOST"]
    DATABASE_PORT = os.environ["DATABASE_PORT"]
    DATABASE_USERNAME = os.environ["DATABASE_USERNAME"]
    DATABASE_PASSWORD = os.environ["DATABASE_PASSWORD"]
    DATABASE_NAME = os.environ["DATABASE_NAME"]
    RECORD_MANAGER_DB_URL = f"postgresql://{DATABASE_USERNAME}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

    # components_docs = load_components_folder()
    components_description = load_components_description()

    embedding = get_embeddings_model()

    client = weaviate.Client(
        url=WEAVIATE_URL,
        auth_client_secret=weaviate.auth.AuthApiKey(WEAVIATE_API_KEY)
    )
    
    vectorstore = Weaviate(
        client=client,
        index_name=WEAVIATE_INDEX_NAME,
        text_key="text",
        embedding=embedding,
        by_text=False,
        attributes=["source", "component_name", "component_version"],
    )

    record_manager = SQLRecordManager(
        f"weaviate/{WEAVIATE_INDEX_NAME}", db_url=RECORD_MANAGER_DB_URL
    )
    record_manager.create_schema()

    logger.info(f"Loaded {len(components_description)} docs from schema")

    indexing_stats = index(
        components_description,
        record_manager,
        vectorstore,
        cleanup="full",
        source_id_key="component_name",
        force_update=(os.environ.get("FORCE_UPDATE") or "false").lower() == "true",
    )

    logger.info(f"Indexing stats: {indexing_stats}")
    num_vecs = client.query.aggregate(WEAVIATE_INDEX_NAME).with_meta_count().do()
    logger.info(
        f"LangChain now has this many vectors: {num_vecs}",
    )

if __name__ == "__main__":
    ingest_docs()
