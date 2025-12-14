"""API rate limiting and DDoS protection."""

from fastapi import Request, HTTPException
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis
import time
from typing import Optional
import os


class RateLimitService:
    """Rate limiting service using Redis."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
    
    async def init(self):
        """Initialize Redis connection."""
        self.redis_client = await redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    
    async def check_rate_limit(
        self,
        request: Request,
        requests_per_minute: int = 100,
        requests_per_second: int = 1000
    ) -> bool:
        """Check if request should be allowed based on rate limits."""
        
        if not self.redis_client:
            await self.init()
        
        # Get client IP
        client_ip = request.client.host
        if forwarded_for := request.headers.get("X-Forwarded-For"):
            client_ip = forwarded_for.split(",")[0].strip()
        
        # Per-minute limit (sliding window)
        rpm_key = f"rate:rpm:{client_ip}"
        rpm_count = await self.redis_client.incr(rpm_key)
        
        if rpm_count == 1:
            await self.redis_client.expire(rpm_key, 60)
        
        if rpm_count > requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": requests_per_minute,
                    "window": "60 seconds",
                    "retry_after": 60
                }
            )
        
        # Per-second limit (DDoS protection)
        current_second = int(time.time())
        rps_key = f"rate:rps:{client_ip}:{current_second}"
        rps_count = await self.redis_client.incr(rps_key)
        
        if rps_count == 1:
            await self.redis_client.expire(rps_key, 2)
        
        if rps_count > requests_per_second:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "DDoS protection triggered",
                    "detail": "Too many requests per second",
                    "retry_after": 1
                }
            )
        
        return True
    
    async def get_remaining(self, request: Request, limit: int = 100) -> int:
        """Get remaining requests in current window."""
        client_ip = request.client.host
        rpm_key = f"rate:rpm:{client_ip}"
        
        current = await self.redis_client.get(rpm_key)
        current_count = int(current) if current else 0
        
        return max(0, limit - current_count)


class BruteForceProtection:
    """Brute force attack protection."""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_attempts: int = 5,
        lockout_time: int = 900  # 15 minutes
    ):
        self.redis_url = redis_url
        self.max_attempts = max_attempts
        self.lockout_time = lockout_time
        self.redis_client: Optional[redis.Redis] = None
    
    async def init(self):
        """Initialize Redis connection."""
        if not self.redis_client:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
    
    async def check_login_attempt(self, user_id: str, success: bool) -> bool:
        """Track login attempts and enforce lockout."""
        
        if not self.redis_client:
            await self.init()
        
        key = f"login:attempts:{user_id}"
        
        # If successful, clear attempts
        if success:
            await self.redis_client.delete(key)
            return True
        
        # Increment failed attempts
        attempts = await self.redis_client.incr(key)
        await self.redis_client.expire(key, self.lockout_time)
        
        if attempts > self.max_attempts:
            ttl = await self.redis_client.ttl(key)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Account temporarily locked",
                    "reason": "Too many failed login attempts",
                    "retry_after": ttl
                }
            )
        
        return False
    
    async def get_remaining_attempts(self, user_id: str) -> int:
        """Get remaining login attempts."""
        if not self.redis_client:
            await self.init()
        
        key = f"login:attempts:{user_id}"
        current = await self.redis_client.get(key)
        current_count = int(current) if current else 0
        
        return max(0, self.max_attempts - current_count)


# Global instances
rate_limiter = RateLimitService(redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"))
brute_force = BruteForceProtection(redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"))


# Dependency for FastAPI routes
async def rate_limit_dependency(request: Request):
    """FastAPI dependency for rate limiting."""
    await rate_limiter.check_rate_limit(request)
    return True
