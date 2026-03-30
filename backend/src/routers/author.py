
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from starlette.status import HTTP_200_OK

from src.database import get_session
from src.models import Book, Chapter,Author


router = APIRouter(
    prefix = "/v1/authors",
    tags = ["Authors"]
)

@router.get("/",description="Get all the authors and their respective books")
def get_full_author_data(session:Session = Depends(get_session)):
    stmt = select(Author)
    response = session.exec(stmt).all()

    if not response:
        raise HTTPException(status_code=404,detail="Not found")
    return response


@router.get("/{author_id}",description="Get the author based on the id")
def get_full_author_data(author_id :int,session:Session = Depends(get_session)):
    response = session.get(Author,author_id)
    if not response:
        raise HTTPException(status_code=404,detail="Not found")

    return response


@router.get("/{author_id}/books", status_code=HTTP_200_OK)
def get_author_books(author_id: int, session: Session = Depends(get_session)):
    author = session.get(Author, author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    bibliography = []
    for book in author.books:
        bibliography.append({
            "id": book.id,
            "title": book.title,
            "publication_year": book.publication_year
        })

    return bibliography