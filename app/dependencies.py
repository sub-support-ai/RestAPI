from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Заглушка для тестов — всегда возвращает тестового пользователя.
    """
    return {"user_id": 1, "role": "user"}


def require_role(required_role: str):
    """
    Зависимость для проверки роли пользователя.
    Используется как: Depends(require_role("admin"))
    """
    async def role_dependency(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_dependency