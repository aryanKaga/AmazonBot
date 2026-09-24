from amazon_bot.schemas import UserContext


class UserRepository:
    """Interface for replacing synthetic data with a real customer repository."""
    def get_context(self, user_id: str) -> UserContext:
        raise NotImplementedError


from datetime import datetime, timedelta

class SyntheticUserRepository(UserRepository):
    def get_context(self, user_id: str) -> UserContext:
        now = datetime.utcnow()
        return UserContext(
            user_id=user_id,
            profile={
                "name": "Demo Customer",
                "email": "demo@example.invalid",
                "phone": "+1-555-0100",
                "created_at": (now - timedelta(days=365)).isoformat(),
                "tier": "gold",
                "locale": "en-US",
                "timezone": "America/New_York",
            },
            orders=[
                {
                    "order_id": "DEMO-1001",
                    "status": "delivered",
                    "placed_at": (now - timedelta(days=30)).isoformat(),
                    "total": 89.97,
                    "currency": "USD",
                    "items": [
                        {"sku": "SKU-100", "name": "Wireless Mouse", "qty": 1, "price": 29.99},
                        {"sku": "SKU-200", "name": "USB-C Hub", "qty": 1, "price": 59.98},
                    ],
                },
                {
                    "order_id": "DEMO-1002",
                    "status": "in_transit",
                    "placed_at": (now - timedelta(days=2)).isoformat(),
                    "total": 149.99,
                    "currency": "USD",
                    "items": [
                        {"sku": "SKU-300", "name": "Mechanical Keyboard", "qty": 1, "price": 149.99},
                    ],
                },
                {
                    "order_id": "DEMO-1003",
                    "status": "cancelled",
                    "placed_at": (now - timedelta(days=90)).isoformat(),
                    "total": 19.99,
                    "currency": "USD",
                    "items": [
                        {"sku": "SKU-050", "name": "Phone Case", "qty": 1, "price": 19.99},
                    ],
                },
            ],
            subscriptions=[
                {
                    "name": "Prime",
                    "status": "active",
                    "started_at": (now - timedelta(days=365)).isoformat(),
                    "renews_at": (now + timedelta(days=30)).isoformat(),
                    "billing_cycle": "annual",
                    "price": 139.00,
                },
                {
                    "name": "Streaming Plus",
                    "status": "trialing",
                    "started_at": (now - timedelta(days=5)).isoformat(),
                    "renews_at": (now + timedelta(days=9)).isoformat(),
                    "billing_cycle": "monthly",
                    "price": 12.99,
                },
            ],
        )