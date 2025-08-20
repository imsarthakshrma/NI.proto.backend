# DNS Configuration Guide for nativeiq.tech

## Overview
This guide provides the exact DNS records you need to configure in your domain registrar for Native IQ deployment.

## Required DNS Records

### For Local Development
**No DNS configuration needed** - uses `localhost:8000`

### For Staging Environment

Configure these records in your **nativeiq.tech** domain registrar:

```
Record Type: A
Name: staging-api
Value: [YOUR_STAGING_SERVER_IP]
TTL: 300 (5 minutes)
```

**Example for common registrars:**

**Cloudflare:**
- Type: `A`
- Name: `staging-api`
- IPv4 address: `YOUR_STAGING_SERVER_IP`
- Proxy status: `DNS only` (gray cloud)

**Namecheap:**
- Type: `A Record`
- Host: `staging-api`
- Value: `YOUR_STAGING_SERVER_IP`
- TTL: `Automatic`

**GoDaddy:**
- Type: `A`
- Name: `staging-api`
- Value: `YOUR_STAGING_SERVER_IP`
- TTL: `1 Hour`

### For Production Environment

Configure these records in your **nativeiq.tech** domain registrar:

```
Record Type: A (or CNAME for AWS ALB)
Name: api
Value: [AWS_LOAD_BALANCER_DNS] or [PRODUCTION_SERVER_IP]
TTL: 300 (5 minutes)
```

**For AWS ALB (Recommended):**
```
Record Type: CNAME
Name: api
Value: your-alb-name-123456789.us-east-1.elb.amazonaws.com
TTL: 300
```

## How to Get the Values

### 1. Staging Server IP
**If deploying to your own server:**
```bash
# Get your server's public IP
curl ifconfig.me
```

**If using cloud provider:**
- **DigitalOcean:** Check Droplet dashboard
- **AWS EC2:** Check instance public IP in console
- **Google Cloud:** Check VM instance external IP

### 2. AWS Load Balancer DNS (Production)
**After running AWS deployment:**
```bash
# Get ALB DNS name
aws elbv2 describe-load-balancers --region us-east-1 --query 'LoadBalancers[0].DNSName' --output text
```

**Or from AWS Console:**
1. Go to EC2 → Load Balancers
2. Find your Native IQ load balancer
3. Copy the DNS name (e.g., `native-iq-alb-123456789.us-east-1.elb.amazonaws.com`)

## Step-by-Step DNS Setup

### Step 1: Access Your Domain Registrar
Log into your domain registrar where you purchased `nativeiq.tech`

### Step 2: Find DNS Management
Look for:
- "DNS Management"
- "DNS Records" 
- "Advanced DNS"
- "Manage DNS"

### Step 3: Add Records
**For Staging:**
1. Click "Add Record" or "+"
2. Select "A Record"
3. Enter `staging-api` in Name/Host field
4. Enter your staging server IP in Value field
5. Save

**For Production:**
1. Click "Add Record" or "+"
2. Select "A Record" (or "CNAME" for AWS ALB)
3. Enter `api` in Name/Host field
4. Enter your production IP or ALB DNS in Value field
5. Save

### Step 4: Verify DNS Propagation
```bash
# Check if DNS is working (may take 5-15 minutes)
nslookup staging-api.nativeiq.tech
nslookup api.nativeiq.tech

# Or use online tools:
# https://dnschecker.org/
```

## SSL Certificate Email
Your deployment scripts use `admin@nativeiq.tech` for Let's Encrypt certificates.

**Make sure this email exists or update it in:**
- `deployment/docker-compose.staging.yml` (line 53)
- `deployment/aws-deploy.sh` (if using AWS ACM)

## Common Registrar Instructions

### Cloudflare
1. Go to cloudflare.com → Dashboard
2. Select `nativeiq.tech` domain
3. Click "DNS" tab
4. Click "Add record"
5. Configure as shown above

### Namecheap
1. Go to namecheap.com → Domain List
2. Click "Manage" next to `nativeiq.tech`
3. Go to "Advanced DNS" tab
4. Click "Add New Record"
5. Configure as shown above

### GoDaddy
1. Go to godaddy.com → My Products
2. Click "DNS" next to `nativeiq.tech`
3. Click "Add" in DNS Records section
4. Configure as shown above

## Testing Your Setup

### Test Staging
```bash
# After DNS propagation (5-15 minutes)
curl -I https://staging-api.nativeiq.tech/health

# Should return HTTP 200 OK
```

### Test Production
```bash
# After production deployment
curl -I https://api.nativeiq.tech/health

# Should return HTTP 200 OK
```

## Troubleshooting

### DNS Not Resolving
- Wait 15-30 minutes for propagation
- Check TTL settings (lower = faster updates)
- Verify record type and values
- Use `nslookup` or `dig` to test

### SSL Certificate Issues
- Verify email `admin@nativeiq.tech` exists
- Check domain ownership
- Ensure port 80/443 are open on server

### Connection Refused
- Verify server is running
- Check firewall settings
- Confirm correct IP address

## Next Steps

1. **Configure DNS records** in your registrar
2. **Wait for propagation** (5-15 minutes)
3. **Deploy staging**: `./deployment/deploy-env.sh staging`
4. **Test staging URL**: `https://staging-api.nativeiq.tech`
5. **Deploy production** when ready

## Quick Reference

| Environment | URL | DNS Record | Points To |
|-------------|-----|------------|-----------|
| Local | `http://localhost:8000` | None | Local machine |
| Staging | `https://staging-api.nativeiq.tech` | A Record | Staging server IP |
| Production | `https://api.nativeiq.tech` | A/CNAME | Production IP/ALB |
