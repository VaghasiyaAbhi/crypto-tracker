# 🚀 AUTOMATIC DEPLOYMENT SETUP - COMPLETE GUIDE

**Date:** November 20, 2025  
**Status:** ✅ **CONFIGURED & READY**

---

## 🎯 What This Does

**Automatic deployment on every `git push`:**
1. You push code to GitHub (main branch)
2. GitHub Actions automatically triggers
3. Connects to your server via SSH
4. Pulls latest code
5. Detects what changed (frontend/backend/nginx)
6. Rebuilds only what changed
7. Restarts affected services
8. Your site is updated! ✨

**No more manual commands needed!** 🎉

---

## ✅ Setup Complete

### **File Created:**
- ✅ `.github/workflows/deploy.yml` - Auto-deployment workflow

### **What It Does:**
1. **Smart Detection:** Only rebuilds services that changed
2. **Frontend Changes:** Rebuilds Docker image with `--no-cache`
3. **Backend Changes:** Restarts services (rebuilds if `requirements.txt` changed)
4. **Nginx Changes:** Restarts Nginx
5. **Migrations:** Runs automatically if migration files changed
6. **Status Report:** Shows deployment result in GitHub Actions

---

## 🔐 GitHub Secrets Required

You need to configure **3 secrets** in your GitHub repository:

### **How to Add Secrets:**

1. Go to: https://github.com/VaghasiyaAbhi/crypto-tracker/settings/secrets/actions

2. Click **"New repository secret"**

3. Add these **3 secrets**:

---

### **Secret 1: SERVER_HOST**

**Name:** `SERVER_HOST`  
**Value:** `46.62.216.158`

```
46.62.216.158
```

---

### **Secret 2: SERVER_USER**

**Name:** `SERVER_USER`  
**Value:** `root`

```
root
```

---

### **Secret 3: SSH_PRIVATE_KEY**

**Name:** `SSH_PRIVATE_KEY`  
**Value:** Your SSH private key

**To get your SSH private key:**

```bash
# On your local machine, run this command:
cat ~/.ssh/id_rsa
```

**Or if you're already using a specific key to SSH to the server:**

```bash
# Find which key you're using
ssh -v root@46.62.216.158 2>&1 | grep "identity file"

# Then display that key
cat ~/.ssh/YOUR_KEY_NAME
```

**Copy the ENTIRE output** including:
```
-----BEGIN OPENSSH PRIVATE KEY-----
...entire key content...
-----END OPENSSH PRIVATE KEY-----
```

**Paste this entire content** as the value for `SSH_PRIVATE_KEY` secret.

---

## ⚠️ Important: SSH Key Setup on Server

**Make sure GitHub Actions can SSH into your server:**

### **Option 1: Use Existing Key (Recommended)**

If you can already SSH to the server from your machine:

```bash
# Your public key should already be in the server's authorized_keys
# Just use the same private key for GitHub secret
```

### **Option 2: Generate New Key for GitHub Actions**

If you want a dedicated key for GitHub Actions:

```bash
# 1. Generate new SSH key pair
ssh-keygen -t rsa -b 4096 -C "github-actions@deploy" -f ~/.ssh/github_actions_key -N ""

# 2. Copy public key to server
ssh-copy-id -i ~/.ssh/github_actions_key.pub root@46.62.216.158

# 3. Display private key for GitHub secret
cat ~/.ssh/github_actions_key
# Copy this entire output to GitHub secret
```

---

## 🧪 Test Your Setup

### **Step 1: Add Secrets to GitHub**

1. Go to: https://github.com/VaghasiyaAbhi/crypto-tracker/settings/secrets/actions
2. Add all 3 secrets (see above)
3. Verify they're saved

### **Step 2: Test SSH Connection**

From your local machine:

```bash
# Make sure you can SSH to server
ssh root@46.62.216.158 "echo 'SSH working!'"
```

Should output: `SSH working!`

### **Step 3: Commit & Push to Test**

Make a small test change:

```bash
cd /Users/virajsavaliya/Desktop/project/Archive\ 2

# Make a small change
echo "# Auto-deploy test" >> README.md

# Commit and push
git add README.md
git commit -m "Test: Auto-deployment"
git push origin main
```

### **Step 4: Watch Deployment**

1. Go to: https://github.com/VaghasiyaAbhi/crypto-tracker/actions
2. You should see a new workflow run starting
3. Click on it to watch the deployment live
4. Should complete in ~2-5 minutes

---

## 📊 Workflow Details

### **Trigger Conditions:**

**Automatic:**
- Push to `main` branch
- Only runs on commits to main

**Manual:**
- Can also trigger manually from GitHub Actions UI
- Useful for re-deploying without new code

### **Smart Rebuild Logic:**

```yaml
Frontend Changes (frontend/*):
  → Stop frontend container
  → Rebuild Docker image (--no-cache)
  → Start fresh container
  ✅ Ensures .env.production changes are applied

Backend Changes (backend/*):
  → Check if requirements.txt changed
    → If yes: Rebuild Docker image
    → If no: Just restart services
  → Restart backend1, celery, celery-beat
  ✅ Fast restarts for code-only changes

Nginx Changes (nginx/*):
  → Restart nginx container
  ✅ Apply new proxy configs

Migration Files (*/migrations/*):
  → Run migrate command automatically
  ✅ Database stays in sync

No Changes:
  → Skip unnecessary rebuilds
  ✅ Fast deployments
```

### **Deployment Steps:**

1. **Checkout Code** (on GitHub runner)
2. **Connect to Server** (via SSH)
3. **Navigate to Project** (`/root/crypto-tracker`)
4. **Pull Latest Code** (`git pull origin main`)
5. **Detect Changes** (compare commits)
6. **Rebuild Services** (only if needed)
7. **Restart Services** (affected ones)
8. **Run Migrations** (if needed)
9. **Show Status** (container health)
10. **Complete!** ✅

---

## 🎯 Usage Guide

### **Normal Development Workflow:**

```bash
# 1. Make your changes locally
cd /Users/virajsavaliya/Desktop/project/Archive\ 2
# Edit files...

# 2. Test locally (optional)
cd frontend
npm run dev  # Test frontend locally

# 3. Commit changes
git add .
git commit -m "Your change description"

# 4. Push to GitHub
git push origin main

# 5. Wait for auto-deployment!
# Check: https://github.com/VaghasiyaAbhi/crypto-tracker/actions

# 6. Verify on live site
# Visit: https://volusignal.com
```

**That's it!** No SSH, no Docker commands, nothing! 🎉

---

## 📝 Example Scenarios

### **Scenario 1: Frontend Change (e.g., UI update)**

```bash
# Edit: frontend/src/app/page.tsx
git add frontend/src/app/page.tsx
git commit -m "Update homepage UI"
git push origin main

# GitHub Actions will:
# ✅ Detect frontend change
# ✅ Rebuild frontend Docker image
# ✅ Start fresh container
# ⏳ Takes ~2-3 minutes
```

### **Scenario 2: Backend Change (e.g., API update)**

```bash
# Edit: backend/core/views.py
git add backend/core/views.py
git commit -m "Add new API endpoint"
git push origin main

# GitHub Actions will:
# ✅ Detect backend change
# ✅ Restart backend services
# ⏳ Takes ~30 seconds
```

### **Scenario 3: Both Frontend + Backend**

```bash
# Edit multiple files
git add .
git commit -m "Full-stack feature: Add notifications"
git push origin main

# GitHub Actions will:
# ✅ Rebuild frontend
# ✅ Restart backend
# ⏳ Takes ~3-4 minutes
```

### **Scenario 4: Just Code Changes (no dependencies)**

```bash
# Edit: backend/core/tasks.py
git add backend/core/tasks.py
git commit -m "Optimize background task"
git push origin main

# GitHub Actions will:
# ✅ Restart backend (no rebuild)
# ⏳ Takes ~20 seconds (fast!)
```

### **Scenario 5: Environment Variable Change**

```bash
# Edit: frontend/.env.production
git add frontend/.env.production
git commit -m "Update API URL"
git push origin main

# GitHub Actions will:
# ✅ Rebuild frontend with --no-cache
# ✅ New env vars baked into build
# ⏳ Takes ~2-3 minutes
```

---

## 🔍 Monitoring Deployments

### **GitHub Actions Page:**

https://github.com/VaghasiyaAbhi/crypto-tracker/actions

**You'll see:**
- ✅ Green checkmark = Success
- ❌ Red X = Failed
- 🟡 Yellow circle = Running
- ⏱️ Deployment time
- 📝 Full logs

### **Email Notifications:**

GitHub will email you:
- ✅ When deployment succeeds
- ❌ When deployment fails
- Can configure in GitHub settings

### **Slack/Discord Notifications (Optional):**

Can add webhooks to get notified in Slack/Discord:
```yaml
- name: Notify Slack
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## 🐛 Troubleshooting

### **Deployment Failed?**

**Check GitHub Actions logs:**
1. Go to: https://github.com/VaghasiyaAbhi/crypto-tracker/actions
2. Click on the failed run
3. Expand the failed step
4. Read the error message

**Common Issues:**

#### **1. SSH Connection Failed**

```
Error: ssh: connect to host 46.62.216.158 port 22: Connection refused
```

**Fix:**
- Check `SSH_PRIVATE_KEY` secret is correct
- Verify public key is in server's `~/.ssh/authorized_keys`
- Test SSH manually: `ssh root@46.62.216.158`

#### **2. Git Pull Failed**

```
Error: Your local changes to the following files would be overwritten
```

**Fix:**
```bash
# On server
ssh root@46.62.216.158
cd /root/crypto-tracker
git reset --hard origin/main
```

#### **3. Docker Build Failed**

```
Error: failed to solve: process "/bin/sh -c npm ci" did not complete successfully
```

**Fix:**
- Check `package.json` syntax
- Verify `requirements.txt` syntax
- Check Docker daemon is running

#### **4. Container Won't Start**

```
Error: container exited with code 1
```

**Fix:**
```bash
# Check logs on server
ssh root@46.62.216.158
docker logs crypto-tracker_frontend_1
# or
docker logs crypto-tracker_backend1_1
```

---

## 🔒 Security Best Practices

### **✅ Do:**
- Use SSH keys (not passwords)
- Store secrets in GitHub Secrets (never in code)
- Use dedicated SSH key for GitHub Actions
- Limit SSH key permissions on server
- Enable 2FA on GitHub account

### **❌ Don't:**
- Commit `.env.local` (already in `.gitignore`)
- Share SSH private keys
- Push secrets to GitHub
- Use root user for application (use in Docker only)
- Disable firewall on server

---

## 📚 Additional Resources

### **GitHub Actions Documentation:**
- https://docs.github.com/en/actions

### **SSH Action Documentation:**
- https://github.com/appleboy/ssh-action

### **Docker Compose Documentation:**
- https://docs.docker.com/compose/

---

## 🎉 Summary

### **What You Get:**

✅ **Automatic Deployment** - Push code, it deploys  
✅ **Smart Rebuilds** - Only rebuilds what changed  
✅ **Fast Deploys** - 30 seconds to 3 minutes  
✅ **Safe Rollbacks** - Can revert via git  
✅ **Deployment History** - All runs logged in GitHub  
✅ **Manual Trigger** - Can re-deploy anytime  
✅ **Error Notifications** - Get alerted on failures  

### **What You Don't Need Anymore:**

❌ Manual SSH to server  
❌ Running Docker commands  
❌ Remembering deployment steps  
❌ Checking if services restarted  
❌ Manual git pulls  
❌ Building Docker images manually  

---

## 🚀 Next Steps

1. **Add GitHub Secrets** (3 secrets - see above)
2. **Test Deployment** (push a small change)
3. **Monitor GitHub Actions** (watch it work!)
4. **Enjoy!** (just push to deploy from now on)

---

## 📞 Quick Reference

### **GitHub Actions Page:**
https://github.com/VaghasiyaAbhi/crypto-tracker/actions

### **Add Secrets:**
https://github.com/VaghasiyaAbhi/crypto-tracker/settings/secrets/actions

### **Your Site:**
https://volusignal.com

### **SSH to Server:**
```bash
ssh root@46.62.216.158
```

### **Manual Deployment (if needed):**
```bash
ssh root@46.62.216.158
cd /root/crypto-tracker
git pull origin main
docker-compose restart frontend backend1
```

---

**Status:** ✅ **READY TO USE**  
**Setup Time:** ~5 minutes (just add secrets)  
**Deployment Time:** 30s - 3min (depending on changes)  
**Last Updated:** November 20, 2025

---

**🎉 That's it! You now have fully automatic deployments!**
