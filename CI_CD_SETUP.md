# 🚀 CI/CD Auto-Deployment Setup Guide

This guide will help you set up automatic deployment whenever you push code to GitHub.

## 📋 Overview

When you push to the `main` branch, GitHub Actions will:
1. ✅ Connect to your server via SSH
2. ✅ Pull the latest code
3. ✅ Rebuild all Docker containers with `--no-cache`
4. ✅ Restart all services (backend, frontend, workers, nginx)
5. ✅ Run database migrations
6. ✅ Collect static files
7. ✅ Show deployment status

## 🔐 Step 1: Add GitHub Secrets

You need to add 3 secrets to your GitHub repository:

### Go to GitHub Settings:
1. Open: https://github.com/VaghasiyaAbhi/crypto-tracker/settings/secrets/actions
2. Click **"New repository secret"** for each of these:

### Secret 1: SERVER_HOST
- **Name**: `SERVER_HOST`
- **Value**: `46.62.216.158`

### Secret 2: SERVER_USER
- **Name**: `SERVER_USER`
- **Value**: `root`

### Secret 3: SERVER_SSH_KEY
- **Name**: `SERVER_SSH_KEY`
- **Value**: Copy the private key below:

```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACAq3ovFUeeOLSecUV5htPsJ8Z9IQi1OGpiI0/9Fl7zbswAAAJhIUlwXSFJc
FwAAAAtzc2gtZWQyNTUxOQAAACAq3ovFUeeOLSecUV5htPsJ8Z9IQi1OGpiI0/9Fl7zbsw
AAAEDn2X0I8dOyj3ZxoQqnmMUh1B36yAEO+VtH5zqVnyDjfCrei8VR544tJ5xRXmG0+wnx
n0hCLU4amIjT/0WXvNuzAAAAFWdpdGh1Yi1hY3Rpb25zLWRlcGxveQ==
-----END OPENSSH PRIVATE KEY-----
```

**⚠️ IMPORTANT**: Copy the ENTIRE key including the BEGIN and END lines!

## ✅ Step 2: Verify Setup

After adding the secrets, the CI/CD is ready to use!

### Test Your Setup:

1. Make any small change (e.g., edit README.md)
2. Commit and push:
   ```bash
   git add .
   git commit -m "Test auto-deployment"
   git push origin main
   ```
3. Watch the deployment:
   - Go to: https://github.com/VaghasiyaAbhi/crypto-tracker/actions
   - You'll see the workflow running
   - Click on it to see live logs

## 🎯 How It Works

### Automatic Trigger:
- Every time you `git push` to `main` branch
- GitHub Actions automatically starts deployment
- Takes about 5-10 minutes (rebuilds everything)

### Manual Trigger:
- Go to: https://github.com/VaghasiyaAbhi/crypto-tracker/actions
- Select "Auto Deploy to Production"
- Click "Run workflow" → "Run workflow"

## 📊 What Happens During Deployment

1. **Pull Code** - Latest changes from GitHub
2. **Rebuild Containers** - All Docker images rebuilt with `--no-cache`
3. **Stop Services** - All containers stopped gracefully
4. **Start Services** - All containers started fresh
5. **Migrations** - Database schema updated
6. **Static Files** - CSS/JS collected
7. **Health Check** - Verify all services running

## 🔧 Deployment Commands

The workflow runs these commands on your server:

```bash
cd /root/crypto-tracker
git pull origin main
docker-compose build --no-cache
docker-compose down
docker-compose up -d
docker-compose exec -T backend1 python manage.py migrate --noinput
docker-compose exec -T backend1 python manage.py collectstatic --noinput
docker-compose ps
```

## ⚡ Quick Deployment Workflow

```bash
# On your local machine:
git add .
git commit -m "Your update message"
git push origin main

# That's it! GitHub Actions does the rest automatically!
# Check progress: https://github.com/VaghasiyaAbhi/crypto-tracker/actions
```

## 📝 Deployment Log

Every deployment shows:
- ✅ Services status
- ✅ Running containers
- ✅ Deployment timestamp
- ✅ Site URL: https://volusignal.com

## 🚨 Troubleshooting

### If deployment fails:

1. **Check GitHub Actions logs**:
   - https://github.com/VaghasiyaAbhi/crypto-tracker/actions
   - Click on the failed workflow
   - Check which step failed

2. **Common issues**:
   - Secrets not configured correctly
   - Server disk space full: `ssh root@46.62.216.158 "df -h"`
   - Docker out of memory: `ssh root@46.62.216.158 "docker system prune -af"`

3. **Manual deployment** (if auto-deploy fails):
   ```bash
   ssh root@46.62.216.158
   cd /root/crypto-tracker
   git pull origin main
   docker-compose down
   docker-compose up -d --build
   ```

## 🎉 Benefits

- ✅ **Zero Downtime**: Services restart smoothly
- ✅ **Always Fresh**: Containers rebuilt every time
- ✅ **Automatic**: No manual server access needed
- ✅ **Safe**: Migrations run automatically
- ✅ **Fast**: Parallel container builds
- ✅ **Trackable**: Full logs in GitHub Actions

## 🔒 Security

- SSH key is stored securely in GitHub Secrets
- Only accessible by GitHub Actions
- Key can be revoked anytime from server
- All traffic encrypted via HTTPS

## 📞 Support

If you need to disable auto-deployment:
1. Go to: https://github.com/VaghasiyaAbhi/crypto-tracker/settings/actions
2. Click "Disable Actions"

To re-enable, just enable Actions again!

---

**🎯 Ready to use!** Just push your next update and watch the magic happen! ✨
