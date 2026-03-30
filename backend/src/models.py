from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
##this is imp revise this shit

class Author(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    birth_year: Optional[int] = None
    bio: Optional[str] = None

    books: List["Book"] = Relationship(back_populates="author")


class Book(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    gutenberg_id: int
    publication_year: Optional[int] = None

    author_id: int = Field(foreign_key="author.id")
    author: Optional["Author"] = Relationship(back_populates="books")

    chapters: List["Chapter"] = Relationship(back_populates="book")


class Chapter(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    chapter_number: int
    title: str
    content: str
    word_count: int

    book_id: int = Field(foreign_key="book.id")

    book: Optional["Book"] = Relationship(back_populates="chapters")
