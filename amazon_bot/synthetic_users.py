from amazon_bot.schemas import UserContext


class UserRepository:
    """Interface for replacing synthetic data with a real customer repository."""
    def get_context(self, user_id: str) -> UserContext:
        raise NotImplementedError


class SyntheticUserRepository(UserRepository):
    def get_context(self, user_id: str) -> UserContext:
        return UserContext(
            user_id=user_id,
            profile={"name": "Demo Customer", "email": "demo@example.invalid"},
            orders=[{"order_id": "DEMO-1001", "status": "hypothetical"}],
            subscriptions=[{"name": "Prime", "status": "hypothetical"}],
        )
