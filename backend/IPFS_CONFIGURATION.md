# 📦 IPFS Configuration Guide

This guide explains how to configure HealChain backend to use your local IPFS Desktop node.

---

## 🎯 Quick Setup for IPFS Desktop

### Step 1: Start IPFS Desktop

1. Open **IPFS Desktop** application
2. Wait for it to fully start (you'll see "IPFS is running" in the status)
3. The local IPFS node will be available at:
   - **API**: `http://localhost:5001`
   - **Gateway**: `http://localhost:8080`

### Step 2: Configure Environment Variables

Add these to your `.env` file in the `backend/` directory:

```bash
# Use local IPFS Desktop node
IPFS_USE_LOCAL=true

# Local IPFS API endpoint (default: http://localhost:5001)
IPFS_API_URL=http://localhost:5001

# Local IPFS Gateway (default: http://localhost:8080)
IPFS_GATEWAY_URL=http://localhost:8080
```

### Step 3: Verify Connection

Test if your IPFS node is running:

```bash
# Check IPFS API
curl http://localhost:5001/api/v0/version

# Should return something like:
# {"Version":"0.xx.x","Commit":"...","Repo":"..."}
```

---

## 🔄 Switching Between Local IPFS and Pinata

### Option 1: Local IPFS Desktop (Recommended for Development)

```bash
# .env configuration
IPFS_USE_LOCAL=true
IPFS_API_URL=http://localhost:5001
IPFS_GATEWAY_URL=http://localhost:8080
```

**Pros**:
- ✅ Free (no API limits)
- ✅ Fast (local network)
- ✅ Full control
- ✅ Good for development

**Cons**:
- ❌ Requires IPFS Desktop running
- ❌ Content only available when your node is online
- ❌ Not suitable for production

### Option 2: Pinata Cloud Service (Recommended for Production)

```bash
# .env configuration
IPFS_USE_LOCAL=false
IPFS_API_URL=https://api.pinata.cloud/pinning/pinJSONToIPFS
IPFS_API_KEY=your_pinata_api_key
IPFS_API_SECRET=your_pinata_secret_key
IPFS_GATEWAY_URL=https://gateway.pinata.cloud/ipfs
```

**Pros**:
- ✅ Always available
- ✅ Pinned content (persistent)
- ✅ Production-ready
- ✅ Global CDN

**Cons**:
- ❌ Requires account and API keys
- ❌ May have rate limits
- ❌ Costs for large usage

---

## 📋 Complete Environment Configuration

### For Local IPFS Desktop

```bash
# IPFS Configuration - Local Desktop
IPFS_USE_LOCAL=true
IPFS_API_URL=http://localhost:5001
IPFS_GATEWAY_URL=http://localhost:8080

# IPFS_API_KEY and IPFS_API_SECRET not needed for local
```

### For Pinata Cloud

```bash
# IPFS Configuration - Pinata
IPFS_USE_LOCAL=false
IPFS_API_URL=https://api.pinata.cloud/pinning/pinJSONToIPFS
IPFS_API_KEY=your_pinata_api_key_here
IPFS_API_SECRET=your_pinata_secret_key_here
IPFS_GATEWAY_URL=https://gateway.pinata.cloud/ipfs
```

---

## 🔍 Troubleshooting

### Error: "Cannot connect to local IPFS node"

**Solution**:
1. Make sure IPFS Desktop is running
2. Check if IPFS is listening on port 5001:
   ```bash
   # Windows PowerShell
   netstat -ano | findstr :5001
   
   # Should show LISTENING
   ```
3. Verify API is accessible:
   ```bash
   curl http://localhost:5001/api/v0/version
   ```

### Error: "ECONNREFUSED"

**Possible causes**:
- IPFS Desktop is not running
- IPFS Desktop is using different ports
- Firewall blocking connection

**Solution**:
1. Check IPFS Desktop settings for API port (usually 5001)
2. Update `IPFS_API_URL` if using custom port
3. Check Windows Firewall settings

### IPFS Desktop Not Starting

**Solution**:
1. Check if another IPFS instance is running
2. Restart IPFS Desktop
3. Check IPFS Desktop logs for errors
4. Try resetting IPFS Desktop settings

---

## 🧪 Testing IPFS Connection

### Test Upload

You can test the IPFS connection by creating a test task that uploads metadata:

```bash
# Start backend
npm run dev

# The backend will automatically use IPFS when:
# - Publishing blocks (M6)
# - Storing model metadata
```

### Manual Test

```bash
# Test IPFS API directly
curl -X POST -F file=@test.json http://localhost:5001/api/v0/add

# Should return:
# {"Name":"test.json","Hash":"Qm...","Size":"123"}
```

---

## 📚 IPFS Desktop Features

### What IPFS Desktop Provides

- **Local IPFS Node**: Full IPFS node running on your machine
- **Web UI**: Access at http://localhost:5001/webui
- **File Manager**: Browse your IPFS content
- **Gateway**: Access content via http://localhost:8080/ipfs/{CID}

### IPFS Desktop Settings

1. Open IPFS Desktop
2. Go to **Settings** → **Advanced**
3. Check **API Address** (default: `/ip4/127.0.0.1/tcp/5001`)
4. Check **Gateway Address** (default: `/ip4/127.0.0.1/tcp/8080`)

---

## 🔐 Security Notes

### Local IPFS (Development)

- ✅ Safe for development
- ✅ No external exposure
- ⚠️ Content only available locally
- ⚠️ Not suitable for production

### Pinata (Production)

- ✅ Secure API keys
- ✅ Content pinned and persistent
- ✅ Global availability
- ⚠️ Keep API keys secret
- ⚠️ Use environment variables, never commit keys

---

## 📖 Additional Resources

- **IPFS Desktop**: https://docs.ipfs.tech/install/ipfs-desktop/
- **IPFS HTTP API**: https://docs.ipfs.tech/reference/kubo/rpc/
- **Pinata Documentation**: https://docs.pinata.cloud/

---

## ✅ Quick Checklist

- [ ] IPFS Desktop installed and running
- [ ] IPFS Desktop shows "IPFS is running"
- [ ] `IPFS_USE_LOCAL=true` in `.env`
- [ ] `IPFS_API_URL=http://localhost:5001` in `.env`
- [ ] Test connection: `curl http://localhost:5001/api/v0/version`
- [ ] Backend can upload to IPFS (check logs)

---

**🎉 Your HealChain backend is now configured to use local IPFS Desktop!**

