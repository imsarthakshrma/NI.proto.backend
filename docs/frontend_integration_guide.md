# Frontend Integration Guide - Google Services OAuth

## 🔐 **How Users Connect Google Services**

This guide shows how to integrate Google Drive, Calendar, and Gmail OAuth from your frontend to the Native IQ backend.

## 🚀 **Quick Setup**

### **1. Add Integration API to Main App**
```python
# In src/api/main.py
from api.integrations_api import router as integrations_router
app.include_router(integrations_router)
```

### **2. Frontend OAuth Flow**

#### **Step 1: Show Available Services**
```javascript
// Get available services
const services = await fetch('/api/integrations/services');
const data = await services.json();

// Display connection buttons for each service
data.services.forEach(service => {
  createConnectionButton(service);
});
```

#### **Step 2: Initiate OAuth**
```javascript
async function connectService(serviceName, userId) {
  const response = await fetch(`/api/integrations/connect/${serviceName}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      frontend_url: window.location.origin
    })
  });
  
  const data = await response.json();
  
  // Redirect user to Google OAuth
  window.location.href = data.auth_url;
}
```

#### **Step 3: Handle OAuth Callback**
```javascript
// Create route: /auth/callback
// This page handles the OAuth return from Google

const urlParams = new URLSearchParams(window.location.search);
const code = urlParams.get('code');
const state = urlParams.get('state');
const error = urlParams.get('error');

if (error) {
  showError(`OAuth failed: ${error}`);
} else if (code && state) {
  // Backend will handle the token exchange
  const response = await fetch(`/api/integrations/callback?code=${code}&state=${state}`);
  const result = await response.json();
  
  if (result.success) {
    showSuccess(`${result.service} connected successfully!`);
    // Redirect back to integrations page
    window.location.href = '/integrations';
  }
}
```

## 🎨 **Frontend UI Components**

### **Integration Status Dashboard**
```javascript
async function loadIntegrationStatus(userId) {
  const response = await fetch(`/api/integrations/status/${userId}`);
  const data = await response.json();
  
  return data.integrations.map(integration => ({
    service: integration.service,
    connected: integration.connected,
    email: integration.email,
    lastConnected: integration.last_connected
  }));
}

// Example UI component
function IntegrationCard({ service, connected, email }) {
  return `
    <div class="integration-card ${connected ? 'connected' : 'disconnected'}">
      <div class="service-info">
        <h3>${service.charAt(0).toUpperCase() + service.slice(1)}</h3>
        <p>${email || 'Not connected'}</p>
      </div>
      <div class="connection-status">
        ${connected 
          ? '<button onclick="disconnectService(\'' + service + '\')">Disconnect</button>'
          : '<button onclick="connectService(\'' + service + '\')">Connect</button>'
        }
      </div>
    </div>
  `;
}
```

### **Connection Flow UI**
```javascript
// Service connection buttons
const serviceButtons = {
  gmail: {
    icon: '📧',
    title: 'Gmail',
    description: 'Send emails and access inbox',
    color: '#EA4335'
  },
  calendar: {
    icon: '📅', 
    title: 'Google Calendar',
    description: 'Schedule meetings and manage events',
    color: '#4285F4'
  },
  drive: {
    icon: '📁',
    title: 'Google Drive', 
    description: 'Access and share files',
    color: '#34A853'
  }
};

function createServiceButton(service, connected) {
  const config = serviceButtons[service];
  return `
    <div class="service-button" style="border-color: ${config.color}">
      <div class="service-icon">${config.icon}</div>
      <div class="service-details">
        <h4>${config.title}</h4>
        <p>${config.description}</p>
      </div>
      <button 
        class="${connected ? 'disconnect-btn' : 'connect-btn'}"
        onclick="${connected ? 'disconnect' : 'connect'}Service('${service}')"
        style="background-color: ${config.color}"
      >
        ${connected ? 'Disconnect' : 'Connect'}
      </button>
    </div>
  `;
}
```

## 🔧 **Complete Integration Functions**

### **Connection Management**
```javascript
class IntegrationManager {
  constructor(userId, apiBaseUrl) {
    this.userId = userId;
    this.apiUrl = apiBaseUrl;
  }
  
  async getStatus() {
    const response = await fetch(`${this.apiUrl}/integrations/status/${this.userId}`);
    return response.json();
  }
  
  async connectService(service) {
    try {
      const response = await fetch(`${this.apiUrl}/integrations/connect/${service}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: this.userId,
          frontend_url: window.location.origin
        })
      });
      
      const data = await response.json();
      
      // Store service info for callback
      localStorage.setItem('connecting_service', service);
      
      // Redirect to OAuth
      window.location.href = data.auth_url;
      
    } catch (error) {
      console.error('Connection failed:', error);
      throw error;
    }
  }
  
  async disconnectService(service) {
    const response = await fetch(
      `${this.apiUrl}/integrations/disconnect/${this.userId}/${service}`,
      { method: 'DELETE' }
    );
    return response.json();
  }
  
  async testConnection(service) {
    const response = await fetch(
      `${this.apiUrl}/integrations/test/${this.userId}/${service}`
    );
    return response.json();
  }
  
  async refreshCredentials(service) {
    const response = await fetch(
      `${this.apiUrl}/integrations/refresh/${this.userId}/${service}`,
      { method: 'POST' }
    );
    return response.json();
  }
}
```

### **OAuth Callback Handler**
```javascript
// OAuth callback page (/auth/callback)
class OAuthCallbackHandler {
  constructor() {
    this.handleCallback();
  }
  
  async handleCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');
    const error = urlParams.get('error');
    
    if (error) {
      this.showError(`Authentication failed: ${error}`);
      return;
    }
    
    if (!code || !state) {
      this.showError('Invalid callback parameters');
      return;
    }
    
    try {
      // Show loading
      this.showLoading('Completing connection...');
      
      // Complete OAuth flow
      const response = await fetch(`/api/integrations/callback?code=${code}&state=${state}`);
      const result = await response.json();
      
      if (result.success) {
        this.showSuccess(
          `${result.service} connected successfully!`,
          result.user_email
        );
        
        // Redirect after success
        setTimeout(() => {
          window.location.href = '/integrations';
        }, 2000);
        
      } else {
        this.showError('Connection failed');
      }
      
    } catch (error) {
      this.showError('Connection error occurred');
      console.error('OAuth callback error:', error);
    }
  }
  
  showLoading(message) {
    document.body.innerHTML = `
      <div class="callback-status loading">
        <div class="spinner"></div>
        <h2>${message}</h2>
      </div>
    `;
  }
  
  showSuccess(message, email) {
    document.body.innerHTML = `
      <div class="callback-status success">
        <div class="success-icon">✅</div>
        <h2>${message}</h2>
        ${email ? `<p>Connected as: ${email}</p>` : ''}
        <p>Redirecting...</p>
      </div>
    `;
  }
  
  showError(message) {
    document.body.innerHTML = `
      <div class="callback-status error">
        <div class="error-icon">❌</div>
        <h2>Connection Failed</h2>
        <p>${message}</p>
        <button onclick="window.location.href='/integrations'">
          Try Again
        </button>
      </div>
    `;
  }
}

// Initialize on callback page
if (window.location.pathname === '/auth/callback') {
  new OAuthCallbackHandler();
}
```

## 🎯 **Complete User Flow**

### **1. Integration Settings Page**
```html
<!-- /integrations page -->
<div class="integrations-page">
  <h1>Connect Your Services</h1>
  <p>Connect your Google services to unlock Native IQ's full potential</p>
  
  <div id="services-grid">
    <!-- Services will be loaded here -->
  </div>
  
  <div id="connection-status">
    <!-- Status will be shown here -->
  </div>
</div>

<script>
const integrationManager = new IntegrationManager('user123', '/api');

async function loadPage() {
  const status = await integrationManager.getStatus();
  renderServices(status.integrations);
}

loadPage();
</script>
```

### **2. Connection Status Indicators**
```css
.integration-card {
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  margin: 10px;
  transition: all 0.3s ease;
}

.integration-card.connected {
  border-color: #4CAF50;
  background-color: #f8fff8;
}

.integration-card.disconnected {
  border-color: #f44336;
  background-color: #fff8f8;
}

.connect-btn {
  background-color: #4285F4;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
}

.disconnect-btn {
  background-color: #f44336;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
}
```

## 🔒 **Security Best Practices**

### **1. Secure Token Storage**
- ✅ Tokens stored server-side with Redis encryption
- ✅ 30-day expiration with automatic refresh
- ✅ State parameter prevents CSRF attacks
- ✅ Secure OAuth redirect validation

### **2. Error Handling**
```javascript
async function safeApiCall(apiFunction) {
  try {
    return await apiFunction();
  } catch (error) {
    if (error.status === 401) {
      // Token expired, redirect to login
      window.location.href = '/login';
    } else if (error.status === 403) {
      // Permission denied
      showError('Permission denied. Please reconnect the service.');
    } else {
      // General error
      showError('Something went wrong. Please try again.');
    }
    throw error;
  }
}
```

## 📱 **Mobile-Friendly Integration**

### **Responsive Design**
```css
@media (max-width: 768px) {
  .services-grid {
    grid-template-columns: 1fr;
  }
  
  .integration-card {
    margin: 5px 0;
    padding: 15px;
  }
  
  .service-button {
    flex-direction: column;
    text-align: center;
  }
}
```

## 🚀 **Testing Integration**

### **Test Endpoints**
```javascript
// Test all connections
async function testAllConnections(userId) {
  const services = ['gmail', 'calendar', 'drive'];
  const results = {};
  
  for (const service of services) {
    try {
      const result = await fetch(`/api/integrations/test/${userId}/${service}`);
      results[service] = await result.json();
    } catch (error) {
      results[service] = { status: 'error', message: error.message };
    }
  }
  
  return results;
}
```

## 🎯 **Summary**

Your users can now:
1. **See available services** - Gmail, Calendar, Drive
2. **Click "Connect"** - Initiates OAuth flow
3. **Authorize with Google** - Secure OAuth redirect
4. **Return to your app** - Automatic token storage
5. **Use integrated features** - Send emails, schedule meetings, access files

The OAuth flow is **completely secure** with state validation, token encryption, and automatic refresh! 🔐✨
