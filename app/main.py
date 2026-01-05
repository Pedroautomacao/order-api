from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.scheduler import start_scheduler
from app.database.deps import get_db
from app.database.imports import * # noqa

from app.users.routes.auth_routes import router as auth_router
from app.users.routes.user_routes import router as user_router
from app.audit.routes.audit_routes import router as audit_router
from app.products.routes.product_routes import router as product_router
from app.clients.routes.client_routes import router as client_router
from app.orders.routes.order_routes import router as order_router
from app.units.routes.unit_Routes import router as unit_router
from app.orders.routes.order_item_routes import router as order_item_router
from app.order_item_breaks.routes.order_item_break_routes import router as order_item_break_router
from app.billing.routes.billing_routes import router as billing_router
from app.dashboard.routes.dashboard_routes import router as dashboard_router
from app.dashboard.routes.dashboard_production_routes import router as dashboard_production_router
from app.dashboard.routes.dashboard_breaks_routes import router as dashboard_breaks_router
from app.dashboard.routes.dashboard_billing_routes import router as dashboard_billing_router
from app.dashboard.routes.dashboard_user_routes import router as dashboard_user_router
from app.dashboard.snapshot.routes.dashboard_snapshot_routes import router as dashboard_snapshot_router
from app.dashboard.routes.dashboard_clients_routes import router as dashboard_clients_router
from app.dashboard.routes.dashboard_products_routes import router as dashboard_products_router
from app.dashboard.routes.dashboard_producers_routes import router as dashboard_producers_router

app = FastAPI(title="Order API")

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)


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
app.include_router(product_router, prefix="/products", tags=["Products"])
app.include_router(order_item_router, prefix="/order-items", tags=["OrderItems"])
app.include_router(order_router, prefix="/orders", tags=["Orders"])
app.include_router(unit_router, prefix="/units", tags=["Units"])
app.include_router(order_item_break_router, prefix="/order-item-breaks", tags=["OrderItems-Breaks"])
app.include_router(billing_router, prefix="/billing", tags=["Billing"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(dashboard_billing_router, prefix="/dashboard-billing", tags=["Dashboard-Billing"])
app.include_router(dashboard_production_router, prefix="/dashboard-production", tags=["Dashboard-Production"])
app.include_router(dashboard_breaks_router, prefix="/dashboard-breaks", tags=["Dashboard-Breaks"])
app.include_router(dashboard_user_router, prefix="/dashboard-user", tags=["Dashboard-User"])
app.include_router(dashboard_snapshot_router, prefix="/dashboard-snapshot", tags=["Dashboard-Snapshot"])
app.include_router(dashboard_clients_router, prefix="/dashboard-clients", tags=["Dashboard-Clients"])
app.include_router(dashboard_products_router, prefix="/dashboard-products", tags=["Dashboard-Products"])
app.include_router(dashboard_producers_router, prefix="/dashboard-producers", tags=["Dashboard-Producers"])


@app.on_event("startup")
def startup_event():
    start_scheduler()

