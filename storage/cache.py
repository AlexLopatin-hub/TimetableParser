import asyncio
import time
from typing import Any, Callable, Optional, TypeVar, overload
from functools import wraps

T = TypeVar("T")


class CacheEntry:
    __slots__ = ("value", "timestamp", "ttl")

    def __init__(self, value: Any, ttl: float):
        self.value = value
        self.timestamp = time.time()
        self.ttl = ttl

    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl


class CacheManager:    
    def __init__(self):
        self._cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired():
                    return entry.value
                else:
                    del self._cache[key]
        return None

    async def set(self, key: str, value: Any, ttl: float) -> None:
        async with self._lock:
            self._cache[key] = CacheEntry(value, ttl)

    async def clear(self, pattern: Optional[str] = None) -> None:
        async with self._lock:
            if pattern is None:
                self._cache.clear()
            else:
                keys_to_delete = [k for k in self._cache.keys() if pattern in k]
                for k in keys_to_delete:
                    del self._cache[k]

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._cache.pop(key, None)


_cache_manager = CacheManager()


def _make_cache_key(*args, **kwargs) -> str:
    filtered_args = [arg for arg in args if not isinstance(arg, type)]
    args_str = "|".join(str(arg) for arg in filtered_args)
    kwargs_str = "|".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return f"{args_str}:{kwargs_str}".replace(" ", "")


def cached(ttl: float):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            cache_key = f"{func.__name__}:{_make_cache_key(*args, **kwargs)}"
            
            cached_value = await _cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            result = await func(*args, **kwargs)
            await _cache_manager.set(cache_key, result, ttl)
            return result
        
        wrapper.clear_cache = lambda: _cache_manager.clear(func.__name__)
        
        return wrapper
    return decorator


async def clear_cache(pattern: Optional[str] = None) -> None:
    await _cache_manager.clear(pattern)


def get_cache_manager() -> CacheManager:
    return _cache_manager
