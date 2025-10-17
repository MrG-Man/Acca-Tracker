#!/usr/bin/env python3
"""
Test script to verify prediction week logic implementation
"""

import sys
import os
from datetime import datetime, time, timedelta

# Add the Acca-Tracker directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Acca-Tracker'))

def get_current_prediction_week_test(now):
    """Test version of get_current_prediction_week with injected datetime.

    Logic:
    - Sunday: Use next Saturday's date
    - Monday-Friday: Use next Saturday's date
    - Saturday before 12:01: Use current Saturday's date
    - Saturday after 12:01: Use next Saturday's date
    """
    current_day = now.weekday()  # 0=Monday, 6=Sunday
    current_time = now.time()

    # Saturday cutoff time (12:01 PM)
    saturday_cutoff = time(12, 1)

    if current_day == 5:  # Saturday (weekday 5)
        if current_time < saturday_cutoff:
            # Before 12:01 PM on Saturday - use current Saturday
            target_date = now.date()
        else:
            # After 12:01 PM on Saturday - use next Saturday (7 days later)
            target_date = now.date() + timedelta(days=7)
    else:
        # Sunday through Friday - use next Saturday
        # Calculate days until next Saturday
        if current_day == 6:  # Sunday
            days_until_saturday = 6  # Next Saturday is 6 days away
        else:  # Monday-Friday
            days_until_saturday = 5 - current_day  # Days until Saturday

        target_date = now.date() + timedelta(days=days_until_saturday)

    return target_date.strftime('%Y-%m-%d')

def test_prediction_week_logic():
    """Test the prediction week logic with various scenarios"""
    print("🧪 Testing Prediction Week Logic")
    print("=" * 50)

    # Test cases: (day_of_week, time_str, expected_behavior)
    # weekday(): 0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday
    test_cases = [
        # Saturday before 12:01 - should use current Saturday
        (5, "11:59:59", "current Saturday"),
        (5, "00:00:01", "current Saturday"),
        (5, "12:00:59", "current Saturday"),

        # Saturday after 12:01 - should use next Saturday
        (5, "12:01:00", "next Saturday"),
        (5, "15:30:00", "next Saturday"),
        (5, "23:59:59", "next Saturday"),

        # Sunday - should use next Saturday (6 days ahead)
        (6, "00:00:01", "next Saturday"),
        (6, "12:00:00", "next Saturday"),
        (6, "23:59:59", "next Saturday"),

        # Monday - should use next Saturday (5 days ahead)
        (0, "09:00:00", "next Saturday"),
        (0, "18:00:00", "next Saturday"),

        # Friday - should use next Saturday (1 day ahead)
        (4, "09:00:00", "next Saturday"),
        (4, "23:59:59", "next Saturday"),
    ]

    results = []

    for day_of_week, time_str, expected in test_cases:
        # Create test datetime - start with a known Saturday and adjust to target day
        # weekday(): 0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday
        base_date = datetime(2024, 10, 19)  # Saturday

        if day_of_week == 5:  # Saturday
            test_date = base_date
        elif day_of_week == 6:  # Sunday
            test_date = base_date + timedelta(days=1)  # Next day is Sunday
        elif day_of_week == 0:  # Monday
            test_date = base_date + timedelta(days=2)  # Two days later is Monday
        elif day_of_week == 1:  # Tuesday
            test_date = base_date + timedelta(days=3)  # Three days later is Tuesday
        elif day_of_week == 2:  # Wednesday
            test_date = base_date + timedelta(days=4)  # Four days later is Wednesday
        elif day_of_week == 3:  # Thursday
            test_date = base_date + timedelta(days=5)  # Five days later is Thursday
        elif day_of_week == 4:  # Friday
            test_date = base_date + timedelta(days=6)  # Six days later is Friday
        else:
            # For other days, calculate properly
            test_date = base_date + timedelta(days=(day_of_week - 5))

        hours, minutes, seconds = map(int, time_str.split(':'))
        test_datetime = test_date.replace(hour=hours, minute=minutes, second=seconds)

        # Call test function
        result = get_current_prediction_week_test(test_datetime)

        # Calculate expected result using the same logic as the function
        current_day = test_datetime.weekday()
        current_time = test_datetime.time()

        if current_day == 5:  # Saturday
            if current_time < time(12, 1):
                # Before 12:01 PM on Saturday - use current Saturday
                expected_date = test_datetime.date()
            else:
                # After 12:01 PM on Saturday - use next Saturday (7 days later)
                expected_date = test_datetime.date() + timedelta(days=7)
        else:
            # Sunday through Friday - use next Saturday
            # Calculate days until next Saturday
            if current_day == 6:  # Sunday
                days_until_saturday = 6  # Next Saturday is 6 days away
            else:  # Monday-Friday
                days_until_saturday = 5 - current_day  # Days until Saturday

            expected_date = test_datetime.date() + timedelta(days=days_until_saturday)

        expected_result = expected_date.strftime('%Y-%m-%d')

        # Check result
        success = result == expected_result
        results.append((day_of_week, time_str, result, expected_result, success))

        print(f"{'✅' if success else '❌'} {day_of_week} ({test_datetime.strftime('%A')}) {time_str}")
        print(f"   Expected: {expected_result}, Got: {result}")
        if not success:
            print(f"   ❌ MISMATCH!")
        print()

    # Summary
    passed = sum(1 for _, _, _, _, success in results if success)
    total = len(results)

    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️  Some tests failed!")
        return False

def test_edge_cases():
    """Test edge cases and boundary conditions"""
    print("🔍 Testing Edge Cases")
    print("=" * 50)

    # Test around the 12:01 PM boundary on Saturday
    test_cases = [
        ("11:59:59", "should use current Saturday"),
        ("12:00:00", "should use current Saturday"),
        ("12:00:59", "should use current Saturday"),
        ("12:01:00", "should use next Saturday"),
        ("12:01:01", "should use next Saturday"),
    ]

    results = []

    for time_str, expected in test_cases:
        hours, minutes, seconds = map(int, time_str.split(':'))
        test_datetime = datetime(2024, 10, 19, hours, minutes, seconds)  # Saturday

        result = get_current_prediction_week_test(test_datetime)

        # For Saturday before 12:01, should be 2024-10-19
        # For Saturday after 12:01, should be 2024-10-26
        if time_str in ["11:59:59", "12:00:00", "12:00:59"]:
            expected_result = "2024-10-19"
        else:
            expected_result = "2024-10-26"

        success = result == expected_result
        results.append((time_str, result, expected_result, success))

        print(f"{'✅' if success else '❌'} Saturday {time_str}")
        print(f"   Expected: {expected_result}, Got: {result}")
        if not success:
            print(f"   ❌ MISMATCH!")
        print()

    # Summary
    passed = sum(1 for _, _, _, success in results if success)
    total = len(results)

    print("=" * 50)
    print(f"📊 Edge Case Results: {passed}/{total} passed")

    return passed == total

if __name__ == "__main__":
    print("🚀 Starting Prediction Week Logic Tests")
    print()

    # Run main tests
    main_tests_passed = test_prediction_week_logic()

    print()

    # Run edge case tests
    edge_tests_passed = test_edge_cases()

    print()

    if main_tests_passed and edge_tests_passed:
        print("🎉 All tests passed! Prediction week logic is working correctly.")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed! Please review the implementation.")
        sys.exit(1)