from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.users.routes.auth_routes import router as auth_router
from app.users.routes.user_routes import router as user_router
from app.audit.routes.audit_routes import router as audit_router
from app.products.routes.product_routes import router as product_router
from app.clients.routes.client_routes import router as client_router
from app.database.deps import get_db
from app.database.imports import * # noqa

app = FastAPI(title="Order API")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/db-health")
def db_health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"database": "ok"}


app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(user_router, prefix="/users", tags=["Users"])
app.include_router(audit_router, prefix="/audit", tags=["Audit"])
app.include_router(client_router, prefix="/clients", tags=["Clients"])
app.include_router(product_router, prefix="/products",tags=["Products"])

