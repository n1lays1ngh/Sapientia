from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from starlette.status import HTTP_200_OK

from src.database import get_session
from src.models import Book, Chapter

router = APIRouter(prefix="/v1",tags = ["Chapters"])

#1. Get the chapters based on the id
@router.get("/chapters/{chapter_id}",status_code=HTTP_200_OK)
def get_chapters(chapter_id:int,session:Session = Depends(get_session)):
    statement = select(Chapter).where(Chapter.id == chapter_id)
    chapters = session.exec(statement).all()

    if not chapters:
        raise HTTPException(status_code=404,detail="Not found")
    return chapters


@router.get("/chapters/{chapter_id}/next",status_code=HTTP_200_OK)
def get_next_chapters(chapter_id:int,session:Session = Depends(get_session)):
    current = session.get(Chapter,chapter_id)
    if not current:
        raise HTTPException(status_code=404,detail="chapter Not Found")

    stmt = select(Chapter).where(
        Chapter.book_id == current.book_id,
        Chapter.chapter_number == current.chapter_number+1
    )

    next_chapter = session.exec(stmt).first()
    if not next_chapter:
        raise HTTPException(status_code=404, detail="You have reached the end of the book.")

    return next_chapter


@router.get("/chapters/{chapter_id}/prev", status_code=HTTP_200_OK)
def get_previous_chapter(chapter_id: int, session: Session = Depends(get_session)):
    current = session.get(Chapter, chapter_id)
    if not current:
        raise HTTPException(status_code=404, detail="Chapter not found")

    statement = select(Chapter).where(
        Chapter.book_id == current.book_id,
        Chapter.chapter_number == current.chapter_number - 1
    )

    prev_chapter = session.exec(statement).first()

    if not prev_chapter:
        raise HTTPException(status_code=404, detail="You are at the beginning of the book.")

    return prev_chapter



"""
POST /v1/chapters/{chapter_id}/bookmark: Saves the user's exact reading position so they can resume later.

POST /v1/chapters/{chapter_id}/highlights
"""
