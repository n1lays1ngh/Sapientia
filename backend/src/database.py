import os

from sqlalchemy import NullPool
from sqlmodel import Session,create_engine
from dotenv import load_dotenv


load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    echo=True,
    # pool_pre_ping=True,
    poolclass=NullPool
)

def get_session():
    with Session(engine) as session:
        yield session

