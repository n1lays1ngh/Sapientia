import os

from sqlalchemy import NullPool
from sqlmodel import Session,create_engine
from dotenv import load_dotenv


load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    echo=True,
    poolclass=NullPool,
    connect_args={"sslmode": "require"}
)

def get_session():
    with Session(engine) as session:
        yield session

