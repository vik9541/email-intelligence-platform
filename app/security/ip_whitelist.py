"""IP whitelist for admin endpoints."""

from fastapi import Request, HTTPException
from typing import List
from ipaddress import ip_address, ip_network, IPv4Address, IPv4Network
import os


# Admin IP whitelist (can be configured via environment)
ADMIN_IP_WHITELIST = os.getenv("ADMIN_IP_WHITELIST", "127.0.0.1,192.168.1.0/24").split(",")


def check_ip_whitelist(client_ip: str, allowed_ips: List[str]) -> bool:
    """Check if client IP is in whitelist.
    
    Args:
        client_ip: Client IP address
        allowed_ips: List of allowed IPs or CIDR ranges
    
    Returns:
        True if IP is whitelisted, False otherwise
    """
    try:
        client = ip_address(client_ip)
        
        for allowed_ip in allowed_ips:
            allowed_ip = allowed_ip.strip()
            
            # Check CIDR range
            if "/" in allowed_ip:
                network = ip_network(allowed_ip, strict=False)
                if client in network:
                    return True
            # Check exact IP
            elif client == ip_address(allowed_ip):
                return True
        
        return False
    
    except ValueError as e:
        # Invalid IP address
        print(f"Invalid IP address: {e}")
        return False


async def verify_admin_access(request: Request):
    """Middleware to verify admin endpoint access.
    
    Raises:
        HTTPException: 403 if IP is not whitelisted
    """
    # Get client IP from request
    client_ip = request.client.host
    
    # Check X-Forwarded-For header (if behind proxy)
    if forwarded_for := request.headers.get("X-Forwarded-For"):
        client_ip = forwarded_for.split(",")[0].strip()
    
    # Check X-Real-IP header (alternative)
    if real_ip := request.headers.get("X-Real-IP"):
        client_ip = real_ip.strip()
    
    # Verify IP is whitelisted
    if not check_ip_whitelist(client_ip, ADMIN_IP_WHITELIST):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Access denied",
                "reason": "IP address not whitelisted for admin access",
                "client_ip": client_ip
            }
        )
    
    return True


async def verify_internal_access(request: Request):
    """Verify access from internal network only.
    
    Allows:
    - Localhost (127.0.0.1, ::1)
    - Private networks (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
    """
    client_ip = request.client.host
    
    if forwarded_for := request.headers.get("X-Forwarded-For"):
        client_ip = forwarded_for.split(",")[0].strip()
    
    try:
        ip = ip_address(client_ip)
        
        # Allow localhost
        if ip.is_loopback:
            return True
        
        # Allow private networks
        if ip.is_private:
            return True
        
        # Deny public IPs
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Access denied",
                "reason": "Internal endpoints only accessible from private network",
                "client_ip": client_ip
            }
        )
    
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid IP address"}
        )
