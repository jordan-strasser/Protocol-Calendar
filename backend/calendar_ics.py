#!/usr/bin/env python3
"""
Universal iCalendar (.ics) file generator for cross-platform calendar support.
Works on Linux, Windows, and macOS. Users can import .ics files into any calendar app.
"""

import os
import re
from datetime import datetime, timedelta
from pathlib import Path
import json


def generate_ics_file(dated_entries, exp_id, output_dir="calendar_exports"):
    """
    Generate an iCalendar (.ics) file from dated entries.
    Returns the path to the generated file.
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{exp_id}_{timestamp}.ics"
    filepath = os.path.join(output_dir, filename)
    
    # Generate ICS content
    ics_content = "BEGIN:VCALENDAR\n"
    ics_content += "VERSION:2.0\n"
    ics_content += "PRODID:-//Lab Protocol Calendar//Lab Calendar Tool//EN\n"
    ics_content += "CALSCALE:GREGORIAN\n"
    ics_content += "METHOD:PUBLISH\n"
    
    # Add each event
    for day_num, task, calendar_date, entry_exp_id in dated_entries:
        # Format date for ICS (YYYYMMDD)
        date_str = calendar_date.strftime("%Y%m%d")
        
        # Create UID for the event
        uid = f"{exp_id}-day{day_num}-{date_str}@lab-calendar"
        
        # Escape special characters in task description
        task_escaped = task.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")
        task_escaped = task_escaped.replace("\n", "\\n")
        
        # Create event
        ics_content += "BEGIN:VEVENT\n"
        ics_content += f"UID:{uid}\n"
        ics_content += f"DTSTART;VALUE=DATE:{date_str}\n"
        ics_content += f"DTEND;VALUE=DATE:{date_str}\n"
        ics_content += f"SUMMARY:ID: {exp_id}, Day {day_num}: {task_escaped}\n"
        ics_content += f"DESCRIPTION:[EXPERIMENT_ID:{exp_id}] {task_escaped}\n"
        ics_content += f"CATEGORIES:Lab Protocol\n"
        ics_content += "STATUS:CONFIRMED\n"
        ics_content += "SEQUENCE:0\n"
        ics_content += "END:VEVENT\n"
    
    ics_content += "END:VCALENDAR\n"
    
    # Write to file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(ics_content)
    
    return filepath


def read_ics_file(ics_filepath):
    """
    Read an .ics file and extract experiment IDs and events.
    Returns a dictionary with experiment IDs and their events.
    """
    matching_ids = {}
    
    if not os.path.exists(ics_filepath):
        return matching_ids
    
    try:
        with open(ics_filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all events
        event_pattern = re.compile(
            r'BEGIN:VEVENT(.*?)END:VEVENT',
            re.DOTALL
        )
        
        id_pattern = re.compile(r'\[EXPERIMENT_ID:([^\]]+)\]', re.IGNORECASE)
        day_pattern = re.compile(r'Day\s+(\d+)', re.IGNORECASE)
        date_pattern = re.compile(r'DTSTART;VALUE=DATE:(\d{8})')
        summary_pattern = re.compile(r'SUMMARY:(.*?)(?:\n|$)')
        
        for event_match in event_pattern.finditer(content):
            event_text = event_match.group(1)
            
            # Extract experiment ID
            id_match = id_pattern.search(event_text)
            if not id_match:
                continue
            
            exp_id = id_match.group(1).strip()
            
            # Extract day number
            day_match = day_pattern.search(event_text)
            if not day_match:
                continue
            
            day_num = int(day_match.group(1))
            
            # Extract date
            date_match = date_pattern.search(event_text)
            if not date_match:
                continue
            
            date_str = date_match.group(1)
            event_date = datetime.strptime(date_str, "%Y%m%d")
            
            # Initialize experiment ID entry if needed
            if exp_id not in matching_ids:
                matching_ids[exp_id] = {
                    'day0_date': None,
                    'events': []
                }
            
            # Store event info (as a dict compatible with extract_day0_from_ics_events)
            matching_ids[exp_id]['events'].append({
                'day': day_num,
                'date': event_date
            })
        
        # Extract Day 0 dates
        for exp_id, exp_data in matching_ids.items():
            day0_date = extract_day0_from_ics_events(exp_data['events'])
            if day0_date:
                exp_data['day0_date'] = day0_date
        
    except Exception as e:
        print(f"Error reading ICS file: {e}")
    
    return matching_ids


def extract_day0_from_ics_events(events):
    """
    Extract Day 0 date from a list of ICS events.
    """
    day0_event = None
    earliest_day = None
    earliest_date = None
    
    for event in events:
        day_num = event['day']
        event_date = event['date']
        
        # If this is Day 0, use it
        if day_num == 0:
            day0_event = event_date
            break
        
        # Track earliest day for fallback
        if earliest_day is None or day_num < earliest_day:
            earliest_day = day_num
            earliest_date = event_date
    
    # If we found Day 0, return it
    if day0_event:
        return day0_event.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Otherwise, calculate Day 0 from the earliest day
    if earliest_date and earliest_day is not None:
        day0_date = earliest_date - timedelta(days=earliest_day)
        return day0_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    return None


def find_matching_ids_in_ics_files(partial_id, calendar_dir="calendar_exports"):
    """
    Find all experiment IDs matching a partial ID by scanning .ics files.
    Returns a dictionary mapping experiment IDs to their Day 0 dates.
    """
    matching_ids = {}
    partial_id_lower = partial_id.lower()
    
    if not os.path.exists(calendar_dir):
        return matching_ids
    
    # Scan all .ics files in the directory
    for filepath in Path(calendar_dir).glob("*.ics"):
        ics_data = read_ics_file(str(filepath))
        
        for exp_id, exp_data in ics_data.items():
            # Check if this ID matches the partial ID
            if partial_id_lower in exp_id.lower():
                if exp_id not in matching_ids:
                    matching_ids[exp_id] = exp_data
                else:
                    # Merge events if we've seen this ID before
                    matching_ids[exp_id]['events'].extend(exp_data['events'])
    
    return matching_ids


def remove_events_from_ics(exp_id, calendar_dir="calendar_exports"):
    """
    Remove events for an experiment ID by regenerating .ics files without those events.
    This is a simple approach - in practice, you might want to keep a master .ics file.
    """
    # For now, we'll just mark that events should be removed
    # In a more sophisticated implementation, you'd maintain a master .ics file
    # and regenerate it, or use a database to track which events to include
    
    # This is a placeholder - in practice, you'd want to:
    # 1. Read all .ics files
    # 2. Remove events matching the exp_id
    # 3. Regenerate the .ics files
    
    # For simplicity, we'll just return True and note that the user should
    # manually delete the .ics file or regenerate it
    return True

