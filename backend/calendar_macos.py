#!/usr/bin/env python3
"""
macOS-specific Apple Calendar integration using EventKit.
This module is only used on macOS systems.
"""

import platform
from datetime import datetime, timedelta
import re


def is_macos():
    """Check if running on macOS."""
    return platform.system() == 'Darwin'


def add_to_calendar(dated_entries, exp_id, calendar_name="Lab Protocols"):
    """
    Add calendar events to Apple Calendar using EventKit.
    Tags events with experiment ID for later deletion.
    """
    if not is_macos():
        return False
    
    try:
        from EventKit import EKEventStore, EKCalendar, EKEvent
        from AppKit import NSDate
    except ImportError:
        print("Error: PyObjC not installed. Install with: pip install pyobjc-framework-EventKit")
        return False
    
    try:
        # Request access to calendar
        event_store = EKEventStore.alloc().init()
        
        # Request calendar access (async)
        import threading
        access_granted = threading.Event()
        
        def access_callback(granted, error):
            if error:
                print(f"Error requesting calendar access: {error}")
            access_granted.set()
        
        event_store.requestAccessToEntityType_completion_(
            0,  # EKEntityTypeEvent
            access_callback
        )
        
        # Wait for access (with timeout)
        access_granted.wait(timeout=5)
        if not access_granted.is_set():
            print("Error: Calendar access request timed out.")
            return False
        
        # Get or create calendar
        calendars = event_store.calendarsForEntityType_(0)  # EKEntityTypeEvent
        calendar = None
        
        for cal in calendars:
            if cal.title() == calendar_name:
                calendar = cal
                break
        
        if calendar is None:
            # Create new calendar
            calendar = EKCalendar.calendarForEntityType_eventStore_(0, event_store)
            calendar.setTitle_(calendar_name)
            # Use default calendar source (usually iCloud or local)
            sources = event_store.sources()
            if sources.count() > 0:
                calendar.setSource_(sources.objectAtIndex_(0))
            else:
                print("Error: No calendar sources available.")
                return False
            
            error = None
            success = event_store.saveCalendar_commit_error_(calendar, True, error)
            if not success:
                print(f"Error: Could not create calendar '{calendar_name}'")
                return False
        
        # Add events
        added_count = 0
        for day_num, task, calendar_date, entry_exp_id in dated_entries:
            event = EKEvent.eventWithEventStore_(event_store)
            
            # Set title with experiment ID
            title = f"ID: {exp_id}, Day {day_num}: {task}"
            event.setTitle_(title)
            
            # Set date (all-day event)
            ns_date_start = NSDate.dateWithTimeIntervalSince1970_(calendar_date.timestamp())
            # Add 1 day for end date (all-day events need end date)
            end_date = calendar_date + timedelta(days=1)
            ns_date_end = NSDate.dateWithTimeIntervalSince1970_(end_date.timestamp())
            
            event.setStartDate_(ns_date_start)
            event.setEndDate_(ns_date_end)
            event.setAllDay_(True)
            
            # Add notes with experiment ID tag for searching
            notes = f"[EXPERIMENT_ID:{exp_id}] {task}"
            event.setNotes_(notes)
            
            event.setCalendar_(calendar)
            
            # Save event
            error = None
            success = event_store.saveEvent_span_commit_error_(event, 0, True, error)  # 0 = EKSpanThisEvent
            if success:
                added_count += 1
            else:
                print(f"Warning: Could not save event for Day {day_num}")
        
        print(f"\n✓ Added {added_count} events to Apple Calendar '{calendar_name}'")
        return True
        
    except Exception as e:
        print(f"Error adding events to Apple Calendar: {e}")
        return False


def remove_from_calendar(exp_id, calendar_name="Lab Protocols"):
    """
    Remove all calendar events tagged with the given experiment ID from Apple Calendar.
    """
    if not is_macos():
        return False
    
    try:
        from EventKit import EKEventStore
        from AppKit import NSDate
        from datetime import datetime, timedelta
    except ImportError:
        print("Error: PyObjC not installed. Install with: pip install pyobjc-framework-EventKit")
        return False
    
    try:
        event_store = EKEventStore.alloc().init()
        
        # Request calendar access (async)
        import threading
        access_granted = threading.Event()
        
        def access_callback(granted, error):
            if error:
                print(f"Error requesting calendar access: {error}")
            access_granted.set()
        
        event_store.requestAccessToEntityType_completion_(
            0,  # EKEntityTypeEvent
            access_callback
        )
        
        # Wait for access (with timeout)
        access_granted.wait(timeout=5)
        if not access_granted.is_set():
            print("Error: Calendar access request timed out.")
            return False
        
        # Find calendar
        calendars = event_store.calendarsForEntityType_(0)
        calendar = None
        
        for cal in calendars:
            if cal.title() == calendar_name:
                calendar = cal
                break
        
        if calendar is None:
            print(f"Error: Calendar '{calendar_name}' not found.")
            return False
        
        # Search for events with the experiment ID tag
        # Search in a wide date range (past 2 years to future 2 years)
        start_date = NSDate.dateWithTimeIntervalSince1970_(
            (datetime.now() - timedelta(days=365*2)).timestamp()
        )
        end_date = NSDate.dateWithTimeIntervalSince1970_(
            (datetime.now() + timedelta(days=365*2)).timestamp()
        )
        
        predicate = event_store.predicateForEventsWithStartDate_endDate_calendars_(
            start_date, end_date, [calendar]
        )
        
        events = event_store.eventsMatchingPredicate_(predicate)
        
        deleted_count = 0
        search_tag = f"[EXPERIMENT_ID:{exp_id}]"
        
        for event in events:
            notes = event.notes()
            title = event.title()
            
            # Check if event is tagged with this experiment ID
            if notes and search_tag in notes:
                # Also check title for experiment ID
                if exp_id in title:
                    error = None
                    success = event_store.removeEvent_span_commit_error_(event, 0, True, error)
                    if success:
                        deleted_count += 1
                    else:
                        print(f"Warning: Could not delete event: {title}")
        
        if deleted_count > 0:
            print(f"✓ Removed {deleted_count} events with experiment ID '{exp_id}' from Apple Calendar")
        else:
            print(f"No events found with experiment ID '{exp_id}'")
        
        return deleted_count > 0
        
    except Exception as e:
        print(f"Error removing events from Apple Calendar: {e}")
        return False


def find_matching_experiment_ids(partial_id, calendar_name="Lab Protocols"):
    """
    Find all experiment IDs in the calendar that contain the partial ID.
    Returns a dictionary mapping experiment IDs to their Day 0 dates.
    """
    if not is_macos():
        return {}
    
    try:
        from EventKit import EKEventStore
        from AppKit import NSDate
        from datetime import datetime, timedelta
        import re
    except ImportError:
        print("Error: PyObjC not installed. Install with: pip install pyobjc-framework-EventKit")
        return {}
    
    try:
        event_store = EKEventStore.alloc().init()
        
        # Request calendar access (async)
        import threading
        access_granted = threading.Event()
        
        def access_callback(granted, error):
            if error:
                print(f"Error requesting calendar access: {error}")
            access_granted.set()
        
        event_store.requestAccessToEntityType_completion_(
            0,  # EKEntityTypeEvent
            access_callback
        )
        
        # Wait for access (with timeout)
        access_granted.wait(timeout=5)
        if not access_granted.is_set():
            print("Error: Calendar access request timed out.")
            return {}
        
        # Find calendar
        calendars = event_store.calendarsForEntityType_(0)
        calendar = None
        
        for cal in calendars:
            if cal.title() == calendar_name:
                calendar = cal
                break
        
        if calendar is None:
            print(f"Error: Calendar '{calendar_name}' not found.")
            return {}
        
        # Search for events in a wide date range
        start_date = NSDate.dateWithTimeIntervalSince1970_(
            (datetime.now() - timedelta(days=365*2)).timestamp()
        )
        end_date = NSDate.dateWithTimeIntervalSince1970_(
            (datetime.now() + timedelta(days=365*2)).timestamp()
        )
        
        predicate = event_store.predicateForEventsWithStartDate_endDate_calendars_(
            start_date, end_date, [calendar]
        )
        
        events = event_store.eventsMatchingPredicate_(predicate)
        
        # Find all experiment IDs matching the partial ID
        matching_ids = {}
        partial_id_lower = partial_id.lower()
        
        # Pattern to extract experiment ID from notes or title
        # Notes format: [EXPERIMENT_ID:XXX] ...
        # Title format: ID: XXX, Day N: ...
        id_pattern = re.compile(r'\[EXPERIMENT_ID:([^\]]+)\]', re.IGNORECASE)
        title_pattern = re.compile(r'ID:\s*([^,]+)', re.IGNORECASE)
        
        for event in events:
            notes = event.notes()
            title = event.title()
            exp_id = None
            
            # Try to extract ID from notes first
            if notes:
                match = id_pattern.search(notes)
                if match:
                    exp_id = match.group(1).strip()
            
            # Try to extract ID from title if not found in notes
            if not exp_id and title:
                match = title_pattern.search(title)
                if match:
                    exp_id = match.group(1).strip()
            
            # Check if this ID matches the partial ID
            if exp_id and partial_id_lower in exp_id.lower():
                if exp_id not in matching_ids:
                    matching_ids[exp_id] = {
                        'day0_date': None,
                        'events': []
                    }
                matching_ids[exp_id]['events'].append(event)
        
        return matching_ids
        
    except Exception as e:
        print(f"Error finding matching experiment IDs: {e}")
        return {}


def extract_day0_from_events(events):
    """
    Extract Day 0 date from a list of calendar events (macOS EventKit events).
    """
    day0_event = None
    earliest_day = None
    earliest_date = None
    
    # Pattern to extract day number from title: "Day N:"
    day_pattern = re.compile(r'Day\s+(\d+)', re.IGNORECASE)
    
    for event in events:
        title = event.title()
        if not title:
            continue
        
        # Extract day number
        match = day_pattern.search(title)
        if match:
            day_num = int(match.group(1))
            
            # Get event date
            start_date = event.startDate()
            if start_date:
                # Convert NSDate to Python datetime
                event_datetime = datetime.fromtimestamp(start_date.timeIntervalSince1970())
                
                # If this is Day 0, use it
                if day_num == 0:
                    day0_event = event_datetime
                    break
                
                # Track earliest day for fallback
                if earliest_day is None or day_num < earliest_day:
                    earliest_day = day_num
                    earliest_date = event_datetime
    
    # If we found Day 0, return it
    if day0_event:
        return day0_event.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Otherwise, calculate Day 0 from the earliest day
    if earliest_date and earliest_day is not None:
        day0_date = earliest_date - timedelta(days=earliest_day)
        return day0_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    return None

