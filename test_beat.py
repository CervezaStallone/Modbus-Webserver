"""Test Beat scheduler directly"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'modbus_webserver.settings')
django.setup()

from django_celery_beat.models import PeriodicTask, IntervalSchedule
from datetime import datetime
from django.utils import timezone

# Check all tasks
print("\n=== Periodic Tasks ===")
for task in PeriodicTask.objects.all():
    print(f"\nTask: {task.name}")
    print(f"  Enabled: {task.enabled}")
    print(f"  Interval: {task.interval}")
    print(f"  Last run: {task.last_run_at}")
    print(f"  Total runs: {task.total_run_count}")
    
    # Check if should run
    if task.interval:
        if task.last_run_at:
            next_run = task.last_run_at + task.interval.schedule.remaining_estimate(task.last_run_at)
            print(f"  Next run: {next_run}")
            print(f"  Should run now: {next_run <= timezone.now()}")
        else:
            print(f"  Should run now: True (never run)")
