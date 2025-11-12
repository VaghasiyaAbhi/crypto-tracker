# 🔧 Session Timeout Fix

## Issue
Users were being logged out after 2-3 minutes of inactivity (e.g., attending a phone call), causing frustration when trying to interact with the website.

## Root Cause
Two conflicting timeout settings were causing premature logout:

1. **Backend JWT Token**: `ACCESS_TOKEN_LIFETIME = 2 minutes` ❌ (Too short!)
2. **Frontend Session**: `SESSION_TIMEOUT = 30 minutes` ✅ (Reasonable, but backend expires first)

The backend JWT token was expiring in just 2 minutes, forcing logout regardless of frontend session settings.

## Solution

### Backend Changes (`backend/project_config/settings.py`)
```python
# BEFORE
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=2),   # ❌ Too short
    'REFRESH_TOKEN_LIFETIME': timedelta(minutes=5),  # ❌ Too short
}

# AFTER
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),   # ✅ 15 minutes
    'REFRESH_TOKEN_LIFETIME': timedelta(minutes=30),  # ✅ 30 minutes
}
```

### Frontend Changes (`frontend/src/lib/auth.ts`)
```typescript
// BEFORE
const SESSION_TIMEOUT = 30 * 60 * 1000; // 30 minutes

// AFTER
const SESSION_TIMEOUT = 15 * 60 * 1000; // 15 minutes (matches backend)
```

## New Behavior

✅ **15 Minutes Session**: Users stay logged in for 15 minutes of inactivity  
✅ **Activity Tracking**: Timer resets on every interaction with the website  
✅ **30 Min Refresh Token**: Additional 30-minute buffer for token refresh  
✅ **No Premature Logout**: Users can take calls, switch tabs, etc. without being logged out

## Timeline

| Time | Old Behavior | New Behavior |
|------|--------------|--------------|
| 0-2 min | ✅ Logged in | ✅ Logged in |
| 2-3 min | ❌ **Logged out** | ✅ Logged in |
| 3-15 min | ❌ Logged out | ✅ Logged in |
| 15+ min | ❌ Logged out | ❌ Logged out |

## Testing

1. Login to https://volusignal.com
2. Wait 2-3 minutes (take a call, switch tabs)
3. Click any button or navigate the site
4. ✅ Should **NOT** be logged out (previously would redirect to login)
5. Wait 15+ minutes without any activity
6. ❌ Should be logged out (security timeout)

## Files Changed

1. **`backend/project_config/settings.py`**
   - Line 246-257: Updated `SIMPLE_JWT` configuration
   - Increased `ACCESS_TOKEN_LIFETIME`: 2 → 15 minutes
   - Increased `REFRESH_TOKEN_LIFETIME`: 5 → 30 minutes

2. **`frontend/src/lib/auth.ts`**
   - Line 17: Updated `SESSION_TIMEOUT` constant
   - Changed from 30 minutes to 15 minutes
   - Updated all related comments

## Deployment

Changes will be automatically deployed via GitHub Actions CI/CD pipeline when pushed to `main` branch.

```bash
git add .
git commit -m "fix: prevent premature logout when switching tabs (2-3 min issue)"
git push origin main
```

Monitor deployment: https://github.com/VaghasiyaAbhi/crypto-tracker/actions

## Security Considerations

✅ **Balanced Security**: 15 minutes provides good security while allowing normal usage patterns  
✅ **Activity-Based**: Timer resets on user activity, not just page load  
✅ **Automatic Logout**: Users are still automatically logged out after inactivity period  
✅ **Token Rotation**: Refresh tokens are rotated for additional security

## User Experience Impact

| Scenario | Before | After |
|----------|--------|-------|
| Phone call (2-3 min) | ❌ Logged out | ✅ Stay logged in |
| Switch tabs briefly | ❌ Sometimes logged out | ✅ Stay logged in |
| Coffee break (5 min) | ❌ Logged out | ✅ Stay logged in |
| Lunch break (30+ min) | ❌ Logged out | ❌ Logged out (expected) |

---

**Status**: ✅ Fixed  
**Deployed**: Auto-deploy on push  
**Effective Date**: Nov 12, 2025
