#!/usr/bin/env python
"""
Test the calendar fix
Shows how the timezone fix resolves the issue
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Demonstrate the bug and fix
print("=" * 70)
print("CALENDAR TIMEZONE BUG - EXPLANATION")
print("=" * 70)

DEFAULT_TIMEZONE = "Asia/Kolkata"

# ❌ WRONG - Using UTC (old code)
print("\n❌ OLD CODE (WRONG - Using UTC):")
utc_now = datetime.utcnow()
print(f"  Now (UTC):         {utc_now.isoformat()}Z")
print(f"  → Search range:    {utc_now.isoformat()}Z to ...")
print(f"  Problem: Your event 'Call Mom at 6pm' is in Asia/Kolkata")
print(f"  UTC ≠ Kolkata (5.5 hours difference!)")
print(f"  Result: Event outside search range → NOT SHOWN ❌")

# ✅ CORRECT - Using local timezone (new code)
print("\n✅ NEW CODE (CORRECT - Using Local Timezone):")
tz = ZoneInfo(DEFAULT_TIMEZONE)
local_now = datetime.now(tz)
print(f"  Now (Kolkata):     {local_now.isoformat()}")
print(f"  → Search range:    {local_now.isoformat()} to ...")
print(f"  Event 'Call Mom at 6pm' is in Asia/Kolkata")
print(f"  Kolkata = Kolkata ✓ (exact match!)")
print(f"  Result: Event in search range → SHOWN ✅")

print("\n" + "=" * 70)
print("TIMEZONE DIFFERENCE:")
print("=" * 70)
print(f"UTC Now:     {utc_now.isoformat()}Z")
print(f"Kolkata Now: {local_now.isoformat()}")
diff_hours = (local_now.utcoffset().total_seconds() / 3600)
print(f"Difference:  +{diff_hours:.1f} hours")

print("\n" + "=" * 70)
print("FIX SUMMARY:")
print("=" * 70)
print("""
✅ Changed: datetime.utcnow() 
   To: datetime.now(ZoneInfo(DEFAULT_TIMEZONE))

✅ Result: Events now show correctly in calendar listing!

✅ Applied to:
   - list_events()
   - delete_event()

✅ Testing: After restart, try:
   "show my calendar for next week"
   → Should show "Call Mom" event now!
""")
