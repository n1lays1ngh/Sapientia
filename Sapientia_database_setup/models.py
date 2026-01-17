from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class Author(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    birth_year: Optional[int] = None
    bio: Optional[str] = None

    books: List["Book"] = Relationship(back_populates="author")


class Book(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    gutenberg_id: int = Field(unique=True, index=True)
    publication_year: Optional[int] = None
    cover_image_url: Optional[str] = None

    author_id: Optional[int] = Field(default=None, foreign_key="author.id")
    author: Optional[Author] = Relationship(back_populates="books")
    chapters: List["Chapter"] = Relationship(back_populates="book")


class Chapter(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    chapter_number: int
    title: Optional[str] = None
    content: str
    word_count: int

    book_id: Optional[int] = Field(default=None, foreign_key="book.id")
    book: Optional[Book] = Relationship(back_populates="chapters")