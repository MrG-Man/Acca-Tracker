#!/usr/bin/env python3
"""
Simple test to understand the prediction week logic
"""

import sys
import os
from datetime import datetime, time, timedelta

# Add the Acca-Tracker directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Acca-Tracker'))

def get_current_prediction_week_test(now):
    """Test version of get_current_prediction_week with injected datetime."""
    current_day = now.weekday()  # 0=Monday, 6=Sunday
    current_time = now.time()

    # Saturday cutoff time (12:01 PM)
    saturday_cutoff = time(12, 1)

    print(f"Input: {now.strftime('%Y-%m-%d %A %H:%M:%S')}")
    print(f"Current day: {current_day}, Current time: {current_time}")

    if current_day == 5:  # Saturday (weekday 5)
        if current_time < saturday_cutoff:
            # Before 12:01 PM on Saturday - use current Saturday
            target_date = now.date()
            print("Logic: Saturday before 12:01 PM -> use current Saturday")
        else:
            # After 12:01 PM on Saturday - use next Saturday (7 days later)
            target_date = now.date() + timedelta(days=7)
            print("Logic: Saturday after 12:01 PM -> use next Saturday")
    else:
        # Sunday through Friday - use next Saturday
        # Calculate days until next Saturday
        if current_day == 6:  # Sunday
            days_until_saturday = 6  # Next Saturday is 6 days away
            print("Logic: Sunday -> next Saturday is 6 days away")
        else:  # Monday-Friday
            days_until_saturday = 5 - current_day  # Days until Saturday
            print(f"Logic: {now.strftime('%A')} -> days until Saturday: {days_until_saturday}")

        target_date = now.date() + timedelta(days=days_until_saturday)

    result = target_date.strftime('%Y-%m-%d')
    print(f"Result: {result}")
    print("-" * 50)
    return result

if __name__ == "__main__":
    print("🔍 Testing Prediction Week Logic with Current Implementation")
    print()

    # Test current time
    now = datetime.now()
    print(f"Current time: {now}")
    print()

    # Test specific scenarios
    test_cases = [
        ("Saturday 11:59", datetime(2024, 10, 19, 11, 59, 59)),  # Saturday before 12:01
        ("Saturday 12:01", datetime(2024, 10, 19, 12, 1, 0)),    # Saturday after 12:01
        ("Sunday 12:00", datetime(2024, 10, 20, 12, 0, 0)),      # Sunday
        ("Monday 12:00", datetime(2024, 10, 21, 12, 0, 0)),      # Monday
        ("Friday 12:00", datetime(2024, 10, 25, 12, 0, 0)),      # Friday
    ]

    for name, test_time in test_cases:
        print(f"Testing {name}:")
        result = get_current_prediction_week_test(test_time)
        print()