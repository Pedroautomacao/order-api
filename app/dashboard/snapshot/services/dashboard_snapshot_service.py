from app.core.time import utcnow
from app.dashboard.services.dashboard_overview_service import DashboardService
from app.dashboard.services.dashboard_production_service import (
    DashboardProductionService,
)
from app.dashboard.services.dashboard_breaks_service import (
    DashboardBreaksService,
)
from app.dashboard.services.dashboard_billing_service import (
    DashboardBillingService,
)
from app.dashboard.services.dashboard_clients_service import (
    DashboardClientsService,
)
from app.dashboard.services.dashboard_products_service import (
    DashboardProductsService,
)
from app.dashboard.services.dashboard_producers_service import (
    DashboardProducersService,
)
from app.dashboard.services.dashboard_user_service import DashboardUsersService
from app.dashboard.snapshot.models.dashboard_snapshot import DashboardSnapshot
from app.ranking.services.rankings_service import RankingsService


class DashboardSnapshotService:
    @staticmethod
    def generate(db):
        payload = {
            # ===== CORE DASHBOARD =====
            "overview": DashboardService.overview(db),
            "production": DashboardProductionService.get(db),
            "breaks": DashboardBreaksService.get(db),
            "billing": DashboardBillingService.get(db),
            "users": DashboardUsersService.get(db),
            "clients": DashboardClientsService.get(db),
            "products": DashboardProductsService.get(db),
            "producers": DashboardProducersService.get(db),
            "rankings": RankingsService.get(db),
        }

        snapshot = DashboardSnapshot(
            generated_at=utcnow(),
            payload=payload,
        )

        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        return snapshot
