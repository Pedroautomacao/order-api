from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.users.routes.auth_routes import router as auth_router
from app.database.deps import get_db
from app.database.imports import * # noqa

app = FastAPI(title="Order API")


@app.get("/health")
def health_check():
    print('OPA')
    return {"status": "ok"}


@app.get("/db-health")
def db_health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"database": "ok"}


app.include_router(auth_router, prefix="/auth", tags=["Auth"])
