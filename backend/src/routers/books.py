from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from starlette.status import HTTP_200_OK

from src.database import get_session
from src.models import Book, Chapter

router  = APIRouter(
    prefix = "/v1/books",
    tags = ["Books"]
)

@router.get("/",status_code=HTTP_200_OK)
async def get_all_books(session : Session = Depends(get_session)):
    statement = select(Book).order_by(Book.id)
    books = session.exec(statement).all()
    return books

@router.get("/{book_id}",status_code=HTTP_200_OK)
async def get_book_by_id(book_id:int,session: Session = Depends(get_session)):
    book = session.get(Book,book_id)
    if not book:
        raise HTTPException(status_code=404,detail="Book Not Found")

    return book

@router.get("/{book_id}/chapters",status_code=HTTP_200_OK)
async def get_toc(book_id:int,session:Session = Depends(get_session)):
    statement = select(Chapter.id,Chapter.chapter_number,Chapter.title).where(Chapter.book_id ==book_id).order_by(Chapter.chapter_number)
    result = session.exec(statement).all()

    if not result:
        raise HTTPException(status_code=404,detail="Not Found")

    toc = [
        {"chapter_id":row.id,"chapter_number" : row.chapter_number , "title" : row.title}
        for row in result
    ]

    return toc









