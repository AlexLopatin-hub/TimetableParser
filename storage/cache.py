import asyncio
import time
from typing import Any, Callable, Optional, TypeVar, overload
from functools import wraps

T = TypeVar("T")


class CacheEntry:
    """Хранит значение с метаданными кеша."""
    __slots__ = ("value", "timestamp", "ttl")

    def __init__(self, value: Any, ttl: float):
        self.value = value
        self.timestamp = time.time()
        self.ttl = ttl

    def is_expired(self) -> bool:
        """Проверить истёк ли TTL."""
        return time.time() - self.timestamp > self.ttl


class CacheManager:
    """Менеджер кеша с поддержкой TTL."""
    
    def __init__(self):
        self._cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Получить значение из кеша, если оно ещё актуально."""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired():
                    return entry.value
                else:
                    del self._cache[key]
        return None

    async def set(self, key: str, value: Any, ttl: float) -> None:
        """Сохранить значение в кеш с TTL."""
        async with self._lock:
            self._cache[key] = CacheEntry(value, ttl)

    async def clear(self, pattern: Optional[str] = None) -> None:
        """Очистить кеш. Если pattern указан, очищает только совпадающие ключи."""
        async with self._lock:
            if pattern is None:
                self._cache.clear()
            else:
                keys_to_delete = [k for k in self._cache.keys() if pattern in k]
                for k in keys_to_delete:
                    del self._cache[k]

    async def delete(self, key: str) -> None:
        """Удалить конкретный ключ из кеша."""
        async with self._lock:
            self._cache.pop(key, None)


# Глобальный менеджер кеша
_cache_manager = CacheManager()


def _make_cache_key(*args, **kwargs) -> str:
    """Создать ключ кеша из аргументов функции."""
    # Исключаем self и cls
    filtered_args = [arg for arg in args if not isinstance(arg, type)]
    args_str = "|".join(str(arg) for arg in filtered_args)
    kwargs_str = "|".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return f"{args_str}:{kwargs_str}".replace(" ", "")


def cached(ttl: float):
    """
    Декоратор для кеширования результатов async функции.
    
    Args:
        ttl: Time-to-live в секундах
    
    Example:
        @cached(ttl=3600)
        async def expensive_operation(group_id: int):
            return await fetch_from_api(group_id)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            cache_key = f"{func.__name__}:{_make_cache_key(*args, **kwargs)}"
            
            # Пытаемся получить из кеша
            cached_value = await _cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Вычисляем и кешируем результат
            result = await func(*args, **kwargs)
            await _cache_manager.set(cache_key, result, ttl)
            return result
        
        # Предоставляем метод для очистки кеша этой функции
        wrapper.clear_cache = lambda: _cache_manager.clear(func.__name__)
        
        return wrapper
    return decorator


async def clear_cache(pattern: Optional[str] = None) -> None:
    """Очистить весь кеш или кеш по паттерну."""
    await _cache_manager.clear(pattern)


def get_cache_manager() -> CacheManager:
    """Получить глобальный менеджер кеша."""
    return _cache_manager
