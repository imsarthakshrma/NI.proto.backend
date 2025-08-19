# API Security & User Isolation Guide

## 🔐 **API Security Architecture**

### **Current Security Implementation**

#### **1. Multi-Layer Authentication**
```python
# Environment-based authorization
TELEGRAM_ALLOWED_GROUPS = "group_id1,group_id2"
TELEGRAM_ALLOWED_USERS = "user_id1,user_id2" 
TELEGRAM_ADMIN_USERS = "admin_id1,admin_id2"
TELEGRAM_DEV_MODE = "false"  # Production security
```

#### **2. Authorization Levels**
- **Admin Users** - Full system access, can modify group permissions
- **Authorized Users** - Individual access regardless of group
- **Group Members** - Access only in authorized groups
- **Development Mode** - Controlled fallback for testing

### **API Endpoint Security**

#### **FastAPI Security Middleware**
```python
# Current CORS configuration needs tightening
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ NEEDS RESTRICTION
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**🚨 Security Recommendations:**
```python
# Production-ready CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend-domain.com",
        "https://app.nativeiq.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

## 👥 **User Identification & Isolation**

### **Individual Chat Tracking**
```python
# Each user gets isolated session context
class ConversationMemory:
    def __init__(self):
        self.conversations = defaultdict(lambda: deque(maxlen=50))
        self.user_profiles = {}
        
    def add_message(self, user_id: str, message: str, is_user: bool = True):
        # Isolated per user_id
        self.conversations[user_id].append({
            "timestamp": datetime.now().isoformat(),
            "content": message,
            "is_user": is_user
        })
```

### **Group Chat User Isolation**
```python
# Group message processing with individual tracking
async def handle_message(self, update: Update, context):
    user = update.effective_user
    chat = update.effective_chat
    
    # Individual user ID (unique across all chats)
    user_id = str(user.id)  # e.g., "123456789"
    
    # Chat context (group vs private)
    chat_type = chat.type  # "private", "group", "supergroup"
    chat_id = str(chat.id)  # Group identifier
    
    # Store with user isolation
    context = {
        "user_id": user_id,           # Individual tracking
        "chat_id": chat_id,           # Group context
        "chat_type": chat_type,       # Private vs group
        "conversation_type": "group" if chat_type != "private" else "direct"
    }
```

### **Memory Isolation Strategy**
```python
# User data completely isolated by user_id
{
    "user_123456": {
        "conversations": [...],
        "profile": {...},
        "session_context": {...}
    },
    "user_789012": {
        "conversations": [...],  # Separate memory
        "profile": {...},
        "session_context": {...}
    }
}
```

## 🛡️ **Security Best Practices**

### **1. API Authentication**
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key for REST endpoints"""
    api_key = credentials.credentials
    
    # Validate against environment variable or database
    valid_keys = os.getenv("NATIVE_IQ_API_KEYS", "").split(",")
    
    if api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return api_key

# Protected endpoint
@app.post("/api/chat")
async def chat_endpoint(message: ChatMessage, api_key: str = Depends(verify_api_key)):
    # Process with verified API key
    pass
```

### **2. User Session Validation**
```python
async def validate_user_session(user_id: str, session_token: str = None):
    """Validate user session and permissions"""
    
    # Check if user exists in authorized users
    if user_id not in authorized_users:
        raise HTTPException(status_code=403, detail="User not authorized")
    
    # Validate session token if provided
    if session_token:
        stored_token = await redis_client.get(f"session:{user_id}")
        if stored_token != session_token:
            raise HTTPException(status_code=401, detail="Invalid session")
    
    return True
```

### **3. Rate Limiting**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/chat")
@limiter.limit("10/minute")  # 10 requests per minute per IP
async def chat_endpoint(request: Request, message: ChatMessage):
    pass
```

### **4. Input Sanitization**
```python
import bleach
from pydantic import validator

class ChatMessage(BaseModel):
    content: str
    user_id: str
    
    @validator('content')
    def sanitize_content(cls, v):
        # Remove potentially dangerous HTML/scripts
        return bleach.clean(v, tags=[], attributes={}, strip=True)
    
    @validator('user_id')
    def validate_user_id(cls, v):
        # Ensure user_id is numeric string
        if not v.isdigit():
            raise ValueError('Invalid user_id format')
        return v
```

## 🔍 **User Tracking Implementation**

### **Group Chat Scenario**
```python
# Group: "Project Team" (chat_id: -1001234567890)
# Users: Alice (123), Bob (456), Carol (789)

async def handle_group_message(update: Update):
    user = update.effective_user  # Alice
    chat = update.effective_chat  # Project Team group
    
    # Individual tracking
    user_id = str(user.id)  # "123" (Alice's unique ID)
    chat_id = str(chat.id)  # "-1001234567890" (group ID)
    
    # Store message with user isolation
    context = {
        "user_id": user_id,           # Alice's individual context
        "chat_id": chat_id,           # Group context for reference
        "message_source": "group",
        "group_members": [123, 456, 789]  # For context only
    }
    
    # Alice's memory is separate from Bob's and Carol's
    conversation_memory.add_message(
        user_id="123",  # Alice's isolated memory
        message=update.message.text,
        metadata={"from_group": chat_id}
    )
```

### **Private Chat Scenario**
```python
# Private chat with Alice (user_id: 123)
async def handle_private_message(update: Update):
    user = update.effective_user  # Alice
    chat = update.effective_chat  # Private chat
    
    user_id = str(user.id)  # "123"
    
    context = {
        "user_id": user_id,
        "chat_id": user_id,  # Same as user_id for private
        "message_source": "private",
        "conversation_type": "direct"
    }
    
    # Same user_id, completely isolated memory
    conversation_memory.add_message(
        user_id="123",  # Alice's same isolated memory
        message=update.message.text,
        metadata={"from_private": True}
    )
```

## 🔒 **Data Protection Measures**

### **1. Encryption at Rest**
```python
import cryptography.fernet

class SecureStorage:
    def __init__(self):
        self.key = os.getenv("ENCRYPTION_KEY").encode()
        self.cipher = Fernet(self.key)
    
    def encrypt_user_data(self, data: dict) -> str:
        """Encrypt sensitive user data"""
        json_data = json.dumps(data)
        encrypted = self.cipher.encrypt(json_data.encode())
        return encrypted.decode()
    
    def decrypt_user_data(self, encrypted_data: str) -> dict:
        """Decrypt user data"""
        decrypted = self.cipher.decrypt(encrypted_data.encode())
        return json.loads(decrypted.decode())
```

### **2. Redis Session Security**
```python
# Secure session storage
async def create_user_session(user_id: str) -> str:
    """Create secure session token"""
    import secrets
    
    session_token = secrets.token_urlsafe(32)
    session_data = {
        "user_id": user_id,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(hours=24)).isoformat()
    }
    
    # Store in Redis with expiration
    await redis_client.setex(
        f"session:{user_id}",
        86400,  # 24 hours
        json.dumps(session_data)
    )
    
    return session_token
```

### **3. Audit Logging**
```python
import logging

audit_logger = logging.getLogger("audit")

async def log_user_action(user_id: str, action: str, details: dict = None):
    """Log user actions for security audit"""
    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "action": action,
        "details": details or {},
        "ip_address": "request.client.host",  # From FastAPI request
        "user_agent": "request.headers.get('user-agent')"
    }
    
    audit_logger.info(json.dumps(audit_entry))
```

## 🎯 **Production Security Checklist**

### **Environment Variables**
```bash
# Required security environment variables
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ALLOWED_GROUPS=group1,group2
TELEGRAM_ALLOWED_USERS=user1,user2
TELEGRAM_ADMIN_USERS=admin1,admin2
TELEGRAM_DEV_MODE=false

# API Security
NATIVE_IQ_API_KEYS=key1,key2,key3
ENCRYPTION_KEY=your_32_byte_key
REDIS_PASSWORD=secure_redis_password

# CORS Origins
ALLOWED_ORIGINS=https://app.nativeiq.com,https://dashboard.nativeiq.com
```

### **Security Headers**
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

# Force HTTPS in production
app.add_middleware(HTTPSRedirectMiddleware)

# Restrict host headers
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["app.nativeiq.com", "api.nativeiq.com"]
)

# Security headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

## 🚀 **Summary**

**Current Security Status:**
- ✅ **User Isolation** - Complete separation by `user_id`
- ✅ **Group/Private Tracking** - Proper context handling
- ✅ **Authorization Layers** - Admin/User/Group permissions
- ⚠️ **API Security** - Needs API key authentication
- ⚠️ **CORS Policy** - Needs production restrictions

**User Tracking:**
- **Individual Chats** - `user_id` directly maps to conversation
- **Group Chats** - `user_id` isolates individual within group context
- **Memory Isolation** - Zero cross-contamination between users
- **Session Context** - Per-user state management

Your system is **architecturally secure** with proper user isolation. The main improvements needed are API authentication and CORS restrictions for production deployment! 🔐✨
