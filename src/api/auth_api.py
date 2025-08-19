"""
API Key Management System for Native IQ Frontend
Generates and validates secure API keys for frontend authentication
"""

import os
import secrets
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import redis
import sys
from pathlib import Path

# Add project paths
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for p in [str(SRC), str(ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()

# Redis connection for key storage
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True
)

# Pydantic models
class APIKeyRequest(BaseModel):
    user_id: str
    app_name: str
    permissions: List[str] = ["chat", "memory", "integrations"]
    expires_in_days: int = 30

class APIKeyResponse(BaseModel):
    api_key: str
    key_id: str
    user_id: str
    app_name: str
    permissions: List[str]
    created_at: str
    expires_at: str
    status: str

class KeyValidationResult(BaseModel):
    valid: bool
    user_id: Optional[str] = None
    permissions: List[str] = []
    expires_at: Optional[str] = None

class APIKeyManager:
    """Manages API key generation, validation, and storage"""
    
    def __init__(self):
        self.key_prefix = "niq_api_key"
        self.user_keys_prefix = "niq_user_keys"
    
    def generate_api_key(self, user_id: str, app_name: str, permissions: List[str], expires_in_days: int = 30) -> Dict:
        """Generate a new API key for a user"""
        
        # Generate secure random key
        key_id = secrets.token_hex(8)  # Short identifier
        api_secret = secrets.token_urlsafe(32)  # Secure secret
        
        # Create the API key format: niq_<key_id>_<hash>
        key_hash = hashlib.sha256(f"{key_id}{api_secret}{user_id}".encode()).hexdigest()[:16]
        api_key = f"niq_{key_id}_{key_hash}"
        
        # Key metadata
        created_at = datetime.now()
        expires_at = created_at + timedelta(days=expires_in_days)
        
        key_data = {
            "key_id": key_id,
            "user_id": user_id,
            "app_name": app_name,
            "permissions": permissions,
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "status": "active",
            "secret_hash": hashlib.sha256(api_secret.encode()).hexdigest()
        }
        
        # Store in Redis
        redis_key = f"{self.key_prefix}:{api_key}"
        redis_client.setex(
            redis_key,
            int(timedelta(days=expires_in_days).total_seconds()),
            json.dumps(key_data)
        )
        
        # Track user's keys
        user_keys_key = f"{self.user_keys_prefix}:{user_id}"
        user_keys = redis_client.get(user_keys_key)
        if user_keys:
            user_keys = json.loads(user_keys)
        else:
            user_keys = []
        
        user_keys.append({
            "api_key": api_key,
            "key_id": key_id,
            "app_name": app_name,
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat()
        })
        
        redis_client.setex(
            user_keys_key,
            int(timedelta(days=expires_in_days + 7).total_seconds()),  # Keep user keys longer
            json.dumps(user_keys)
        )
        
        return {
            "api_key": api_key,
            "key_id": key_id,
            "user_id": user_id,
            "app_name": app_name,
            "permissions": permissions,
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "status": "active"
        }
    
    def validate_api_key(self, api_key: str) -> KeyValidationResult:
        """Validate an API key and return user info"""
        
        if not api_key.startswith("niq_"):
            return KeyValidationResult(valid=False)
        
        # Get key data from Redis
        redis_key = f"{self.key_prefix}:{api_key}"
        key_data = redis_client.get(redis_key)
        
        if not key_data:
            return KeyValidationResult(valid=False)
        
        try:
            key_info = json.loads(key_data)
            
            # Check if key is active
            if key_info.get("status") != "active":
                return KeyValidationResult(valid=False)
            
            # Check expiration
            expires_at = datetime.fromisoformat(key_info["expires_at"])
            if datetime.now() > expires_at:
                # Mark as expired
                key_info["status"] = "expired"
                redis_client.setex(redis_key, 86400, json.dumps(key_info))  # Keep for 1 day
                return KeyValidationResult(valid=False)
            
            return KeyValidationResult(
                valid=True,
                user_id=key_info["user_id"],
                permissions=key_info["permissions"],
                expires_at=key_info["expires_at"]
            )
            
        except Exception:
            return KeyValidationResult(valid=False)
    
    def revoke_api_key(self, api_key: str, user_id: str) -> bool:
        """Revoke an API key"""
        
        redis_key = f"{self.key_prefix}:{api_key}"
        key_data = redis_client.get(redis_key)
        
        if not key_data:
            return False
        
        try:
            key_info = json.loads(key_data)
            
            # Verify ownership
            if key_info["user_id"] != user_id:
                return False
            
            # Mark as revoked
            key_info["status"] = "revoked"
            key_info["revoked_at"] = datetime.now().isoformat()
            
            redis_client.setex(redis_key, 86400, json.dumps(key_info))  # Keep for audit
            return True
            
        except Exception:
            return False
    
    def list_user_keys(self, user_id: str) -> List[Dict]:
        """List all API keys for a user"""
        
        user_keys_key = f"{self.user_keys_prefix}:{user_id}"
        user_keys = redis_client.get(user_keys_key)
        
        if not user_keys:
            return []
        
        try:
            keys = json.loads(user_keys)
            
            # Get current status for each key
            for key_info in keys:
                redis_key = f"{self.key_prefix}:{key_info['api_key']}"
                key_data = redis_client.get(redis_key)
                
                if key_data:
                    full_key_info = json.loads(key_data)
                    key_info["status"] = full_key_info.get("status", "unknown")
                    key_info["permissions"] = full_key_info.get("permissions", [])
                else:
                    key_info["status"] = "expired"
            
            return keys
            
        except Exception:
            return []

# Initialize key manager
key_manager = APIKeyManager()

# Dependency for API key validation
async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> KeyValidationResult:
    """Verify API key from Authorization header"""
    
    api_key = credentials.credentials
    validation_result = key_manager.validate_api_key(api_key)
    
    if not validation_result.valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return validation_result

# API Endpoints
@router.post("/generate-key", response_model=APIKeyResponse)
async def generate_api_key(request: APIKeyRequest):
    """Generate a new API key for frontend authentication"""
    
    try:
        # Validate permissions
        valid_permissions = ["chat", "memory", "integrations", "dashboard", "admin"]
        invalid_perms = [p for p in request.permissions if p not in valid_permissions]
        
        if invalid_perms:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid permissions: {invalid_perms}"
            )
        
        # Generate the key
        key_data = key_manager.generate_api_key(
            user_id=request.user_id,
            app_name=request.app_name,
            permissions=request.permissions,
            expires_in_days=request.expires_in_days
        )
        
        return APIKeyResponse(**key_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Key generation failed: {str(e)}")

@router.get("/validate")
async def validate_key(validation: KeyValidationResult = Depends(verify_api_key)):
    """Validate an API key (used internally)"""
    
    return {
        "valid": validation.valid,
        "user_id": validation.user_id,
        "permissions": validation.permissions,
        "expires_at": validation.expires_at
    }

@router.get("/keys/{user_id}")
async def list_user_api_keys(user_id: str, validation: KeyValidationResult = Depends(verify_api_key)):
    """List all API keys for a user"""
    
    # Users can only see their own keys (or admins can see any)
    if validation.user_id != user_id and "admin" not in validation.permissions:
        raise HTTPException(status_code=403, detail="Access denied")
    
    keys = key_manager.list_user_keys(user_id)
    return {"user_id": user_id, "api_keys": keys}

@router.delete("/revoke/{api_key}")
async def revoke_api_key(api_key: str, validation: KeyValidationResult = Depends(verify_api_key)):
    """Revoke an API key"""
    
    success = key_manager.revoke_api_key(api_key, validation.user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="API key not found or access denied")
    
    return {"message": "API key revoked successfully", "api_key": api_key}

@router.get("/permissions")
async def get_available_permissions():
    """Get list of available permissions"""
    
    return {
        "permissions": [
            {"name": "chat", "description": "Access chat endpoints"},
            {"name": "memory", "description": "Access memory and search endpoints"},
            {"name": "integrations", "description": "Access Google services integration"},
            {"name": "dashboard", "description": "Access dashboard and analytics"},
            {"name": "admin", "description": "Administrative access"}
        ]
    }

# Helper function for other modules
def get_current_user(validation: KeyValidationResult = Depends(verify_api_key)) -> str:
    """Get current user ID from validated API key"""
    return validation.user_id

def require_permission(required_permission: str):
    """Decorator to require specific permission"""
    def permission_checker(validation: KeyValidationResult = Depends(verify_api_key)):
        if required_permission not in validation.permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Permission '{required_permission}' required"
            )
        return validation
    return permission_checker
