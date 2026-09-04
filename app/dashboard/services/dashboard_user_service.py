from sqlalchemy.orm import Session
from sqlalchemy import func

from app.orders.enums import OrderStatus
from app.users.models.user import User
from app.orders.models.order import Order
from app.orders.models.work_order import WorkOrder


class DashboardUsersService:
    @staticmethod
    def get(db: Session):
        producers = (
            db.query(User)
            .filter(User.is_deleted.is_(False))
            .all()
        )

        producing_now_subq = (
            db.query(Order.assigned_user_id)
            .filter(Order.status == OrderStatus.PRODUCING)
            .subquery()
        )

        stats = (
            db.query(
                WorkOrder.user_id,
                func.count(WorkOrder.id),
                func.avg(WorkOrder.time_to_produced_secs),
            )
            .filter(
                WorkOrder.is_deleted.is_(False),
                WorkOrder.time_to_produced_secs.isnot(None),
            )
            .group_by(WorkOrder.user_id)
            .all()
        )

        stats_map = {
            user_id: (total, avg or 0)
            for user_id, total, avg in stats
        }

        users_response = []
        producing_users = 0

        for user in producers:
            is_producing = (
                db.query(producing_now_subq)
                .filter(
                    producing_now_subq.c.assigned_user_id == user.id
                )
                .count()
                > 0
            )

            if is_producing:
                producing_users += 1

            total_orders, avg_time = stats_map.get(user.id, (0, 0))

            users_response.append(
                {
                    "user_id": user.id,
                    "producing_now": is_producing,
                    "total_orders": total_orders,
                    "avg_order_time_secs": round(avg_time, 2),
                }
            )

        idle_users = len(producers) - producing_users

        return {
            "producing_users": producing_users,
            "idle_users": idle_users,
            "users": users_response,
        }
