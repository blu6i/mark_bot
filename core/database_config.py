import os, dotenv
from contextlib import contextmanager, asynccontextmanager
from typing import Any, List, Optional

import asyncpg
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
dotenv.load_dotenv()

class Database:
    def __init__(self, async_mode: bool = False):
        self._async_mode = async_mode
        self._config = {
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "database": os.getenv("DB_NAME"),
            "host": os.getenv("DB_HOST"),
            "port": int(os.getenv("DB_PORT", 5432)),
            "timeout": 5
        }
        self._pool = None


    def init_pool_sync(self, minconn=1, maxconn=10):
        """Инициализация синхронного пула"""
        if self._pool is None:
            self._pool = pool.SimpleConnectionPool(minconn, maxconn, **self._config)

    async def init_pool_async(self, min_size=1, max_size=10):
        """Инициализация асинхронного пула"""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(min_size=min_size, max_size=max_size, **self._config)

    async def init_pool(self, **kwargs):
        """Выбор и инициализация пула по режиму"""
        if self._async_mode:
            await self.init_pool_async(**kwargs)
        else:
            self.init_pool_sync(**kwargs)


    @contextmanager
    def connection_sync(self):
        """Синхронный контекстный менеджер с commit/rollback"""
        if self._pool is None:
            self.init_pool_sync()
        conn = self._pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    @asynccontextmanager
    async def connection_async(self):
        """Асинхронный контекстный менеджер с транзакцией"""
        if self._pool is None:
            await self.init_pool_async()
        conn = await self._pool.acquire()
        try:
            async with conn.transaction():
                yield conn
        finally:
            await self._pool.release(conn)

    def connection(self):
        """Выбираем контекстный менеджер по режиму"""
        if self._async_mode:
            return self.connection_async()
        else:
            return self.connection_sync()


    async def select(self, sql: str, params: Optional[List[Any]] = None, fetchone: bool = False):
        if self._async_mode:
            async with self.connection_async() as conn:
                if fetchone:
                    return await conn.fetchrow(sql, *(params or ()))
                else:
                    return await conn.fetch(sql, *(params or ()))
        else:
            with self.connection_sync() as conn:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute(sql, params or ())
                result = cur.fetchone() if fetchone else cur.fetchall()
                cur.close()
                return result


    async def execute(self, sql: str, params: Optional[List[Any]] = None, returning: bool = False):
        if self._async_mode:
            async with self.connection_async() as conn:
                if returning:
                    row = await conn.fetchrow(sql, *(params or ()))
                    return row['id'] if row else None
                else:
                    await conn.execute(sql, *(params or ()))
                    return True
        else:
            with self.connection_sync() as conn:
                cur = conn.cursor()
                cur.execute(sql, params or ())
                if returning:
                    res = cur.fetchone()
                    cur.close()
                    return res[0] if res else None
                conn.commit()
                cur.close()
                return True


    async def insert(self, sql: str, params: Optional[List[Any]] = None, returning: bool = False):
        return await self.execute(sql, params, returning=returning)

    async def update(self, sql: str, params: Optional[List[Any]] = None, returning: bool = False):
        return await self.execute(sql, params, returning=returning)

    async def delete(self, sql: str, params: Optional[List[Any]] = None, returning: bool = False):
        return await self.execute(sql, params, returning=returning)


    async def close_pool(self):
        if self._pool is not None:
            if self._async_mode:
                await self._pool.close()
            else:
                self._pool.closeall()
            self._pool = None

db_async = Database(async_mode=True)
