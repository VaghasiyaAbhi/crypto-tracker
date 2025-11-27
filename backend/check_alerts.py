#!/usr/bin/env python
"""
Quick script to check active alerts in the database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_config.settings')
django.setup()

from core.models import Alert, User

print("\n" + "="*80)
print("ACTIVE ALERTS IN DATABASE")
print("="*80 + "\n")

active_alerts = Alert.objects.filter(is_active=True).select_related('user')

if not active_alerts.exists():
    print("✅ NO ACTIVE ALERTS FOUND")
else:
    for alert in active_alerts:
        print(f"Alert ID: {alert.id}")
        print(f"  User: {alert.user.email}")
        print(f"  Type: {alert.alert_type}")
        print(f"  Coin: {alert.coin_symbol if alert.coin_symbol else 'ANY COIN'}")
        print(f"  Threshold: {alert.condition_value}")
        print(f"  Channels: {alert.notification_channels}")
        print(f"  Created: {alert.created_at}")
        print(f"  Triggered: {alert.trigger_count} times")
        print(f"  Last Triggered: {alert.last_triggered}")
        print(f"  Active: {alert.is_active}")
        print("-" * 80)

print(f"\nTotal Active Alerts: {active_alerts.count()}\n")
