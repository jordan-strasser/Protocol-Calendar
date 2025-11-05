#!/usr/bin/env python3
"""
Simple HTTP server for the Calendar Parser web UI.
Serves the HTML interface and handles form submissions.
"""

import http.server
import socketserver
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime
import tempfile
from io import BytesIO
import email
from email import message_from_bytes

# Import calendar parser functions
backend_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(os.path.dirname(backend_dir), 'frontend')
sys.path.insert(0, backend_dir)

try:
    from calendar_parser import (
        extract_text_from_pdf, extract_text_from_docx, extract_text_from_doc,
        parse_day_entries, parse_date, assign_dates, extract_title_and_id,
        add_to_apple_calendar, remove_from_apple_calendar,
        find_matching_experiment_ids, extract_day0_from_events
    )
except ImportError as e:
    print(f"Error importing calendar_parser: {e}")
    print(f"Make sure calendar_parser.py is in {backend_dir}")
    sys.exit(1)


class CalendarHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        """Serve the HTML file and static assets."""
        if self.path == '/' or self.path == '/index.html':
            self.path = '/calendar_web.html'
        
        if self.path == '/calendar_web.html' or self.path.startswith('/'):
            try:
                # Serve from frontend directory
                file_path = self.path.lstrip('/')
                if file_path == 'calendar_web.html' or file_path == '':
                    file_path = 'calendar_web.html'
                
                full_path = os.path.join(frontend_dir, file_path)
                
                if os.path.exists(full_path) and os.path.isfile(full_path):
                    # Determine content type
                    if file_path.endswith('.html'):
                        content_type = 'text/html'
                    elif file_path.endswith('.css'):
                        content_type = 'text/css'
                    elif file_path.endswith('.js'):
                        content_type = 'application/javascript'
                    else:
                        content_type = 'application/octet-stream'
                    
                    with open(full_path, 'rb') as f:
                        self.send_response(200)
                        self.send_header('Content-type', content_type)
                        self.end_headers()
                        self.wfile.write(f.read())
                else:
                    self.send_error(404, "File not found")
            except Exception as e:
                self.send_error(500, f"Server error: {str(e)}")
    
    def parse_multipart(self, post_data, boundary):
        """Parse multipart form data manually."""
        form_data = {}
        file_data = None
        
        # Split by boundary
        parts = post_data.split(b'--' + boundary)
        
        for part in parts:
            if b'Content-Disposition' not in part:
                continue
            
            # Parse headers and body
            header_end = part.find(b'\r\n\r\n')
            if header_end == -1:
                continue
            
            headers_text = part[:header_end].decode('utf-8', errors='ignore')
            body = part[header_end + 4:]
            
            # Remove trailing boundary markers
            if body.endswith(b'\r\n--\r\n'):
                body = body[:-7]
            elif body.endswith(b'--\r\n'):
                body = body[:-5]
            
            # Parse Content-Disposition
            if 'name=' in headers_text:
                name_start = headers_text.find('name="') + 6
                name_end = headers_text.find('"', name_start)
                field_name = headers_text[name_start:name_end]
                
                # Check if it's a file
                if 'filename=' in headers_text:
                    filename_start = headers_text.find('filename="') + 10
                    filename_end = headers_text.find('"', filename_start)
                    filename = headers_text[filename_start:filename_end]
                    file_data = {'filename': filename, 'data': body}
                else:
                    # Regular field
                    value = body.decode('utf-8', errors='ignore').strip()
                    form_data[field_name] = value
        
        return form_data, file_data
    
    def do_POST(self):
        """Handle form submissions."""
        if self.path == '/api/process':
            try:
                # Parse multipart form data
                content_type = self.headers['Content-Type']
                if not content_type.startswith('multipart/form-data'):
                    self.send_error(400, "Invalid content type")
                    return
                
                # Get boundary
                boundary_str = content_type.split('boundary=')[1]
                boundary = boundary_str.encode()
                
                # Read the request body
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                # Parse form data
                form_data, file_data = self.parse_multipart(post_data, boundary)
                
                action = form_data.get('action', 'parse')
                exp_id = form_data.get('expId', '').strip()
                day0_date_str = form_data.get('day0Date', '')
                calendar_name = form_data.get('calendarName', 'Lab Protocols').strip()
                
                result = {'success': False, 'message': '', 'error': ''}
                
                if action == 'remove':
                    # Remove from calendar
                    if not exp_id:
                        result['error'] = 'Experiment ID is required'
                    else:
                        try:
                            success = remove_from_apple_calendar(exp_id, calendar_name)
                            if success:
                                result['success'] = True
                                result['message'] = f'Successfully removed events with ID "{exp_id}" from calendar'
                            else:
                                result['error'] = f'No events found with ID "{exp_id}" or calendar not found'
                        except Exception as e:
                            result['error'] = str(e)
                
                elif action == 'update':
                    # Update calendar: find matching IDs, extract Day 0, remove old events, add new ones
                    if not file_data:
                        result['error'] = 'Please select a protocol file'
                    elif not exp_id:
                        result['error'] = 'Experiment ID pattern is required (e.g., "enc" to match enc1, enc2, etc.)'
                    else:
                        try:
                            # Find all experiment IDs matching the partial ID
                            matching_ids = find_matching_experiment_ids(exp_id, calendar_name)
                            
                            if not matching_ids:
                                result['error'] = f'No experiments found matching ID pattern "{exp_id}"'
                                return
                            
                            # Extract Day 0 dates for each matching ID
                            for exp_id_full, exp_data in matching_ids.items():
                                day0_date = extract_day0_from_events(exp_data['events'])
                                if day0_date:
                                    exp_data['day0_date'] = day0_date
                                else:
                                    # If we can't extract Day 0, skip this ID
                                    result['error'] = f'Could not extract Day 0 date for experiment ID "{exp_id_full}"'
                                    return
                            
                            # Save uploaded file temporarily
                            filename = file_data['filename']
                            file_content = file_data['data']
                            
                            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
                                tmp_file.write(file_content)
                                tmp_path = tmp_file.name
                            
                            try:
                                # Parse the file once
                                file_ext = Path(filename).suffix.lower()
                                
                                if file_ext == '.pdf':
                                    text = extract_text_from_pdf(tmp_path)
                                elif file_ext == '.docx':
                                    text = extract_text_from_docx(tmp_path)
                                elif file_ext == '.doc':
                                    text = extract_text_from_doc(tmp_path)
                                else:
                                    result['error'] = f'Unsupported file type: {file_ext}'
                                    return
                                
                                # Parse day entries
                                entries = parse_day_entries(text)
                                if not entries:
                                    result['error'] = 'No Day entries found in the document'
                                    return
                                
                                # Update each matching experiment ID
                                message = f'Found {len(matching_ids)} experiment(s) matching "{exp_id}":\n\n'
                                total_updated = 0
                                
                                for exp_id_full, exp_data in matching_ids.items():
                                    day0_date = exp_data['day0_date']
                                    
                                    # Remove old events for this ID
                                    remove_success = remove_from_apple_calendar(exp_id_full, calendar_name)
                                    
                                    # Assign dates using the extracted Day 0
                                    dated_entries = assign_dates(entries, day0_date, exp_id_full)
                                    
                                    # Add new events to calendar
                                    add_success = add_to_apple_calendar(dated_entries, exp_id_full, calendar_name)
                                    
                                    if add_success:
                                        message += f'✓ Updated "{exp_id_full}" (Day 0: {day0_date.strftime("%Y-%m-%d")}): {len(dated_entries)} events\n'
                                        total_updated += 1
                                    else:
                                        message += f'✗ Failed to update "{exp_id_full}"\n'
                                
                                if total_updated > 0:
                                    result['success'] = True
                                    result['message'] = f'{message}\n✓ Successfully updated {total_updated} experiment(s) in calendar "{calendar_name}"'
                                else:
                                    result['error'] = 'Failed to update any experiments'
                            
                            finally:
                                # Clean up temp file
                                try:
                                    os.unlink(tmp_path)
                                except:
                                    pass
                        
                        except Exception as e:
                            result['error'] = f'Error updating calendar: {str(e)}'
                
                else:
                    # Parse and optionally add to calendar
                    if not file_data:
                        result['error'] = 'Please select a protocol file'
                    elif not exp_id:
                        result['error'] = 'Experiment ID is required'
                    else:
                        try:
                            # Save uploaded file temporarily
                            filename = file_data['filename']
                            file_content = file_data['data']
                            
                            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
                                tmp_file.write(file_content)
                                tmp_path = tmp_file.name
                            
                            try:
                                # Parse the file
                                file_ext = Path(filename).suffix.lower()
                                
                                if file_ext == '.pdf':
                                    text = extract_text_from_pdf(tmp_path)
                                elif file_ext == '.docx':
                                    text = extract_text_from_docx(tmp_path)
                                elif file_ext == '.doc':
                                    text = extract_text_from_doc(tmp_path)
                                else:
                                    result['error'] = f'Unsupported file type: {file_ext}'
                                    return
                                
                                # Parse day entries
                                entries = parse_day_entries(text)
                                if not entries:
                                    result['error'] = 'No Day entries found in the document'
                                    return
                                
                                # Parse Day 0 date
                                if day0_date_str:
                                    day0_date = datetime.strptime(day0_date_str, '%Y-%m-%d')
                                else:
                                    day0_date = datetime.now()
                                
                                day0_date = day0_date.replace(hour=0, minute=0, second=0, microsecond=0)
                                
                                # Assign dates
                                dated_entries = assign_dates(entries, day0_date, exp_id)
                                
                                message = f'Parsed {len(dated_entries)} day entries successfully!\n\n'
                                for day_num, task, cal_date, eid in dated_entries:
                                    date_str = cal_date.strftime("%A, %B %d, %Y")
                                    message += f'Day {day_num:3d} ({date_str}):\n'
                                    message += f'  ID: {eid}, Day {day_num}: {task}\n\n'
                                
                                if action == 'add':
                                    # Add to calendar
                                    success = add_to_apple_calendar(dated_entries, exp_id, calendar_name)
                                    if success:
                                        result['success'] = True
                                        result['message'] = f'{message}\n✓ Added {len(dated_entries)} events to Apple Calendar "{calendar_name}"'
                                    else:
                                        result['error'] = 'Failed to add events to calendar'
                                else:
                                    # Parse only
                                    result['success'] = True
                                    result['message'] = message
                            
                            finally:
                                # Clean up temp file
                                try:
                                    os.unlink(tmp_path)
                                except:
                                    pass
                        
                        except Exception as e:
                            result['error'] = f'Error processing file: {str(e)}'
                
                # Send response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            
            except Exception as e:
                self.send_error(500, f"Server error: {str(e)}")
        else:
            self.send_error(404, "Not found")
    
    def log_message(self, format, *args):
        """Override to reduce log noise."""
        pass




def main():
    PORT = 8001  # Changed to 8001 to avoid conflicts
    
    print(f"=" * 60)
    print(f"Calendar Parser Web Server")
    print(f"=" * 60)
    print(f"Frontend: {frontend_dir}")
    print(f"Backend:  {backend_dir}")
    print(f"Server:   http://localhost:{PORT}")
    print(f"=" * 60)
    print()
    
    try:
        with socketserver.TCPServer(("", PORT), CalendarHandler) as httpd:
            print(f"✓ Server started successfully!")
            print(f"✓ Open http://localhost:{PORT} in your browser")
            print(f"✓ Press Ctrl+C to stop, or run: ./stop_server.sh\n")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✓ Server stopped.")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\n✗ Error: Port {PORT} is already in use.")
            print(f"  Run: ./stop_server.sh")
            print(f"  Or change the PORT in calendar_server.py\n")
        else:
            print(f"\n✗ Error: {e}\n")


if __name__ == '__main__':
    main()

