# Lab Protocol Calendar Parser

A cross-platform tool to parse lab protocol documents and automatically add events to your calendar. Works on Linux, Windows, and macOS.

## Project Structure

```
lab_calendar/
├── backend/
│   ├── calendar_parser.py      # Core parsing logic
│   ├── calendar_server.py      # HTTP server for web UI
│   ├── calendar_platform.py    # Platform-agnostic calendar interface
│   ├── calendar_macos.py       # macOS-specific Apple Calendar integration
│   └── calendar_ics.py         # Universal iCalendar (.ics) file generator
├── frontend/
│   └── calendar_web.html       # Web UI interface
├── Protocols/                   # Protocol files directory
├── calendar_exports/            # Generated .ics files (Linux/Windows)
├── start_server.sh              # Server launcher script
├── requirements.txt             # Core Python dependencies (all platforms)
├── requirements-macos.txt      # macOS-specific dependencies
└── README.md                    # This file
```

## Quick Start

### 1. Install Dependencies

**For all platforms (Linux, Windows, macOS):**
```bash
pip3 install --user --break-system-packages -r requirements.txt
```

**For macOS only (Apple Calendar integration):**
```bash
pip3 install --user --break-system-packages -r requirements-macos.txt
```

Note: On Linux and Windows, the tool will generate `.ics` (iCalendar) files that you can import into Google Calendar, Outlook, or any calendar app. On macOS, if EventKit is available, events are added directly to Apple Calendar.

### 2. Start the Web Server

```bash
./start_server.sh
```

Or directly:
```bash
python3 backend/calendar_server.py
```

### 3. Open in Browser

Open `http://localhost:8001` in your browser.

### 4. Stop the Server

To stop the server:
```bash
./stop_server.sh
```

Or press `Ctrl+C` in the terminal where the server is running.

## Usage

### Web UI (Recommended)

1. Start the server: `./start_server.sh`
2. Open `http://localhost:8001` in your browser
3. Fill in the form:
   - Select a protocol file (PDF, DOC, DOCX)
   - Enter Experiment ID
   - Set Day 0 date (or use "Today" button)
   - Choose Calendar name
4. Click one of the action buttons:
   - **Add to Calendar**: Parse and add events to Apple Calendar
   - **Update Calendar**: Update existing calendar events by removing old ones and adding new ones from the updated protocol file. Uses partial ID matching (e.g., "enc" matches enc1, enc2, enc3, etc.) and automatically extracts Day 0 dates from existing events.
   - **Parse Only**: Preview the parsed calendar
   - **Remove from Calendar**: Remove events by Experiment ID

### Command Line

```bash
# Parse protocol
python3 backend/calendar_parser.py "Protocols/protocol.docx" --id ENC

# Parse and add to calendar
python3 backend/calendar_parser.py "Protocols/protocol.docx" --id ENC --add-to-calendar --day0 11/05/2025

# Remove from calendar
python3 backend/calendar_parser.py --remove-from-calendar --id ENC
```

## Features

- **Cross-platform support**: Works on Linux, Windows, and macOS
  - **macOS**: Direct integration with Apple Calendar (if EventKit available)
  - **Linux/Windows**: Generates `.ics` files for import into any calendar app
- Parses PDF, DOC, and DOCX protocol files
- Extracts Day entries (e.g., "Day 0:", "Day 1:", etc.)
- Assigns calendar dates with Day 0 as today (or custom date)
- Adds events to calendar with experiment ID tagging
- Updates existing events by partial ID matching (e.g., "enc" matches enc1, enc2, etc.)
- Removes events by experiment ID
- Beautiful web interface
- Command-line interface

## Protocol Format

Your protocol document should have entries like:

```
Day 0: EB Formation. 96-well ULA round bottom plate.
Day 3: ½ EB media replacement. Replace half of the media.
Day 5: 24-well transfer. Transfer EBs to Ultra-low attachment plate.
```

The script extracts text after "Day X:" up to the first period.

## Dependencies

**Core (all platforms):**
- PyPDF2 or pdfplumber (for PDF parsing)
- python-docx (for DOCX parsing)

**macOS only (optional):**
- pyobjc-framework-EventKit (for Apple Calendar integration)

Install core dependencies:
```bash
pip3 install --user --break-system-packages -r requirements.txt
```

Install macOS-specific dependencies (macOS only):
```bash
pip3 install --user --break-system-packages -r requirements-macos.txt
```

**Note for Linux/Windows users:** The tool will generate `.ics` files in the `calendar_exports/` directory. You can import these files into Google Calendar, Outlook, Thunderbird, or any calendar application that supports iCalendar format.

## Notes

- The web server runs on port 8001 by default
- Events are tagged with `[EXPERIMENT_ID:XXX]` in the notes for easy deletion
- Calendar name defaults to "Lab Protocols" but can be customized
- All events are created as all-day events
