import os


def get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


class Settings:
    def __init__(self) -> None:
        self.mysql_host = get_env("MYSQL_HOST", "127.0.0.1")
        self.mysql_port = int(get_env("MYSQL_PORT", "3306"))
        self.mysql_user = get_env("MYSQL_USER", "root")
        self.mysql_password = get_env("MYSQL_PASSWORD", "")
        self.mysql_db = get_env("MYSQL_DB", "agent_project")

        self.redis_host = get_env("REDIS_HOST", "127.0.0.1")
        self.redis_port = int(get_env("REDIS_PORT", "6379"))
        self.redis_password = get_env("REDIS_PASSWORD", "")

        self.session_ttl_hours = int(get_env("SESSION_TTL_HOURS", "72"))
        self.max_sessions = int(get_env("MAX_SESSIONS", "5"))


settings = Settings()
