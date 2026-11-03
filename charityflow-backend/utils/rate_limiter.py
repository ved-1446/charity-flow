import time
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, HTTPException, status
from config import TRUST_PROXY

class InMemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int = 60, action_name: str = "requests"):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.action_name = action_name
        self.records: Dict[str, List[float]] = defaultdict(list)

    def check(self, ip: str):
        now = time.time()
        window_start = now - self.window_seconds
        # Clean timestamps older than current window
        self.records[ip] = [t for t in self.records[ip] if t > window_start]
        if len(self.records[ip]) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: maximum {self.max_requests} {self.action_name} per minute allowed for this IP."
            )
        self.records[ip].append(now)

login_limiter = InMemoryRateLimiter(max_requests=10, window_seconds=60, action_name="login attempts")
register_limiter = InMemoryRateLimiter(max_requests=5, window_seconds=60, action_name="registrations")
contact_limiter = InMemoryRateLimiter(max_requests=5, window_seconds=60, action_name="contact messages")

def get_client_ip(request: Request) -> str:
    if TRUST_PROXY:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def rate_limit_login(request: Request):
    ip = get_client_ip(request)
    login_limiter.check(ip)

def rate_limit_register(request: Request):
    ip = get_client_ip(request)
    register_limiter.check(ip)

def rate_limit_contact(request: Request):
    ip = get_client_ip(request)
    contact_limiter.check(ip)

