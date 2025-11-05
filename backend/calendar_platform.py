#!/usr/bin/env python3
"""
Platform-agnostic calendar interface.
Auto-detects platform and uses the appropriate backend (macOS EventKit or universal iCalendar).
"""

import platform
import os


def get_platform():
    """Get the current platform."""
    return platform.system()


def is_macos():
    """Check if running on macOS."""
    return get_platform() == 'Darwin'


# Platform detection and backend selection
_calendar_backend = None


def _init_backend():
    """Initialize the appropriate calendar backend."""
    global _calendar_backend
    
    if _calendar_backend is not None:
        return _calendar_backend
    
    if is_macos():
        # Try to use macOS EventKit
        try:
            from calendar_macos import (
                add_to_calendar as macos_add,
                remove_from_calendar as macos_remove,
                find_matching_experiment_ids as macos_find,
                extract_day0_from_events as macos_extract_day0
            )
            _calendar_backend = {
                'type': 'macos',
                'add': macos_add,
                'remove': macos_remove,
                'find': macos_find,
                'extract_day0': macos_extract_day0
            }
            return _calendar_backend
        except ImportError:
            # Fall back to ICS if EventKit not available
            pass
    
    # Use universal iCalendar (.ics) backend
    try:
        from calendar_ics import (
            generate_ics_file,
            find_matching_ids_in_ics_files,
            extract_day0_from_ics_events,
            remove_events_from_ics
        )
        _calendar_backend = {
            'type': 'ics',
            'add': lambda entries, exp_id, cal_name: _ics_add_wrapper(generate_ics_file, entries, exp_id),
            'remove': lambda exp_id, cal_name: _ics_remove_wrapper(remove_events_from_ics, exp_id),
            'find': lambda partial_id, cal_name: find_matching_ids_in_ics_files(partial_id),
            'extract_day0': extract_day0_from_ics_events
        }
        return _calendar_backend
    except ImportError:
        raise ImportError("Could not import calendar backend modules")


def _ics_add_wrapper(generate_func, entries, exp_id):
    """Wrapper for ICS add function."""
    filepath = generate_func(entries, exp_id)
    print(f"\n✓ Generated calendar file: {filepath}")
    print(f"  You can import this .ics file into Google Calendar, Outlook, or any calendar app.")
    return True


def _ics_remove_wrapper(remove_func, exp_id):
    """Wrapper for ICS remove function."""
    # For ICS, we can't directly remove from calendar apps
    # But we can mark events for removal in our tracking
    result = remove_func(exp_id)
    if result:
        print(f"✓ Marked events for removal. Regenerate .ics files to see changes.")
    return result


def add_to_calendar(dated_entries, exp_id, calendar_name="Lab Protocols"):
    """
    Add events to calendar. Platform-agnostic interface.
    On macOS: Adds directly to Apple Calendar.
    On Linux/Windows: Generates .ics file for import.
    """
    backend = _init_backend()
    return backend['add'](dated_entries, exp_id, calendar_name)


def remove_from_calendar(exp_id, calendar_name="Lab Protocols"):
    """
    Remove events from calendar. Platform-agnostic interface.
    On macOS: Removes from Apple Calendar.
    On Linux/Windows: Marks for removal in ICS tracking.
    """
    backend = _init_backend()
    return backend['remove'](exp_id, calendar_name)


def find_matching_experiment_ids(partial_id, calendar_name="Lab Protocols"):
    """
    Find all experiment IDs matching a partial ID.
    Platform-agnostic interface.
    """
    backend = _init_backend()
    return backend['find'](partial_id, calendar_name)


def extract_day0_from_events(events):
    """
    Extract Day 0 date from events.
    Platform-agnostic interface.
    """
    backend = _init_backend()
    
    # Check if events are macOS EventKit events or ICS event dicts
    if backend['type'] == 'macos':
        from calendar_macos import extract_day0_from_events
        return extract_day0_from_events(events)
    else:
        # ICS events are dicts with 'day' and 'date' keys
        from calendar_ics import extract_day0_from_ics_events
        return extract_day0_from_ics_events(events)


def get_backend_type():
    """Get the type of backend being used."""
    backend = _init_backend()
    return backend['type']

