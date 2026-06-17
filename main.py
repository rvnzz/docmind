import os

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_litellm.embeddings import LiteLLMEmbeddings
from langchain_postgres import PGVector

load_dotenv(dotenv_path=".env", verbose=True)

model = ChatAnthropic(
    model_name=os.getenv("MODEL_NAME"),
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
)

embedding_model = LiteLLMEmbeddings(
    model=os.getenv("EMBEDDING_MODEL_NAME"),
    api_base=os.getenv("EMBEDDING_BASE_URL"),
    api_key=os.getenv("EMBEDDING_API_KEY"),
)

vector_store = PGVector(
    embeddings=embedding_model,
    collection_name="docmind",
    connection=os.getenv("PGVECTOR_CONNECTION"),
)

# print(model.invoke("Привет"))