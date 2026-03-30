from fastapi import FastAPI,Depends
from starlette.status import HTTP_200_OK
from src.routers.books import router as books
from src.routers.chapters import router as chapters
from src.routers.author import router as author
from src.database import get_session
from sqlmodel import Session, select,text
app = FastAPI(
    title="Sapientia API",
    description="The main engine for free book reading",
    version="1.0.0"

)

app.include_router(books)
app.include_router(chapters)
app.include_router(author)
@app.get("/",status_code=HTTP_200_OK,tags = ["Health"])
def health_check():
    return{
        "Status":"Server Working just Fine"
    }


@app.get("/test-db", tags=["Database"])
def test_db_connection(session: Session = Depends(get_session)):
    try:
        # Run a simple query to ask Postgres what version it is
        result = session.exec(text("SELECT version();")).first()
        return {"status": "success", "database_version": result[0]}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

