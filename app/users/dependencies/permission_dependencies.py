def require_permission(permission_code: str):
    def dependency():
        raise NotImplementedError

    return dependency
