# Lab Protocol Calendar Parser

A tool to parse lab protocol documents and automatically add events to Apple Calendar.

## Project Structure

```
lab_calendar/
├── backend/
│   ├── calendar_parser.py    # Core parsing logic and Apple Calendar integration
│   └── calendar_server.py     # HTTP server for web UI
├── frontend/
│   └── calendar_web.html      # Web UI interface
├── Protocols/                 # Protocol files directory
├── start_server.sh           # Server launcher script
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Quick Start

### 1. Install Dependencies

```bash
pip3 install --user --break-system-packages -r requirements.txt
```

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

- Parses PDF, DOC, and DOCX protocol files
- Extracts Day entries (e.g., "Day 0:", "Day 1:", etc.)
- Assigns calendar dates with Day 0 as today (or custom date)
- Adds events to Apple Calendar with experiment ID tagging
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

- PyPDF2 or pdfplumber (for PDF parsing)
- python-docx (for DOCX parsing)
- pyobjc-framework-EventKit (for Apple Calendar integration)

Install all with:
```bash
pip3 install --user --break-system-packages -r requirements.txt
```

## Notes

- The web server runs on port 8001 by default
- Events are tagged with `[EXPERIMENT_ID:XXX]` in the notes for easy deletion
- Calendar name defaults to "Lab Protocols" but can be customized
- All events are created as all-day events
