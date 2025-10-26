import redis
from contextlib import contextmanager
import dotenv, os
dotenv.load_dotenv()

class RedisDatabase:
    def __init__(self, use_pool=True, prefix=""):
        """
        :param use_pool: использовать пул соединений
        :param prefix: префикс для ключей (например 'auth_teacher' или 'student')
        """
        self.config = {
            "host": os.getenv("RD_HOST"),
            "port": os.getenv("RD_PORT"),
            "password": os.getenv("RD_PASSWORD"),
            "db": 0,
            "decode_responses": True
        }
        self.use_pool = use_pool
        self._pool = None
        self._client = None
        self.prefix = prefix

    def init_pool(self, max_connections=10):
        if self.use_pool and self._pool is None:
            self._pool = redis.ConnectionPool(max_connections=max_connections, **self.config)

    def get_client(self):
        if self.use_pool:
            if self._pool is None:
                self.init_pool()
            if self._client is None:
                self._client = redis.Redis(connection_pool=self._pool)
            return self._client
        else:
            if self._client is None:
                self._client = redis.Redis(**self.config)
            return self._client

    @contextmanager
    def connection(self):
        client = self.get_client()
        try:
            yield client
        finally:
            pass

    # ===== Удобные методы с префиксом =====
    def _full_key(self, key: str) -> str:
        if self.prefix:
            return f"{self.prefix}:{key}"
        return key

    def set(self, key, value, ex: int = 300):
        """
        Сохраняет ключ с TTL, по умолчанию 300
        :param key: ключ для записи
        :param value: значение для записи
        :param ex: TTL, по умолчанию 5 минут
        """
        with self.connection() as r:
            r.set(self._full_key(key), value, ex=ex)

    def get(self, key):
        """
        Получает значение по ключу
        :param key: ключ записи
        """
        with self.connection() as r:
            return r.get(self._full_key(key))

    def delete(self, key):
        """
        Удаляет ключ
        :param key: ключ записи
        """
        with self.connection() as r:
            r.delete(self._full_key(key))

    def exists(self, key) -> bool:
        """
        Проверяет, существует ли ключ в Redis
        :param key: ключ для проверки
        :return: True если ключ есть, False если нет
        """
        with self.connection() as r:
            return r.exists(self._full_key(key)) > 0


redis_instance = RedisDatabase(use_pool=True, prefix="lesson_instance")
redis_auth_user = RedisDatabase(use_pool=False, prefix="auth_user")
redis_attendance = RedisDatabase(use_pool=True, prefix="rd_attendance")
redis_link_teacher = RedisDatabase(use_pool=False, prefix="rd_link_teacher")
