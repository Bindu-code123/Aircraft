from dataclasses import dataclass, asdict
from datetime import date, datetime
from enum import Enum
import time
from flask import Flask, render_template_string, jsonify, request
import os
import json
import socket

app = Flask(__name__)

class MaintenanceStatus(Enum):
	SCHEDULED = "Scheduled"
	IN_PROGRESS = "In Progress"
	COMPLETED = "Completed"

	@staticmethod
	def get_next_status(current_status):
		"""Get the next status in order"""
		order = [MaintenanceStatus.SCHEDULED, MaintenanceStatus.IN_PROGRESS, MaintenanceStatus.COMPLETED]
		try:
			current_index = order.index(current_status)
			if current_index < len(order) - 1:
				return order[current_index + 1]
			return None  # Already at final status
		except ValueError:
			return None


@dataclass
class Aircraft:
	aircraft_id: str
	name: str
	status: MaintenanceStatus
	maintenance_date: date
	engineer_name: str


AIRCRAFT_FILE = 'aircraft_data.json'
AUDIT_LOG_FILE = 'audit_log.json'

# Audit Logging System
def add_audit_log(action: str, aircraft_id: str, details: dict):
	"""Add entry to audit log"""
	try:
		logs = []
		if os.path.exists(AUDIT_LOG_FILE):
			with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
				logs = json.load(f)
		
		log_entry = {
			'timestamp': datetime.now().isoformat(),
			'action': action,
			'aircraft_id': aircraft_id,
			'details': details
		}
		logs.append(log_entry)
		
		with open(AUDIT_LOG_FILE, 'w', encoding='utf-8') as f:
			json.dump(logs, f, indent=2)
	except Exception as e:
		print(f"Error adding audit log: {e}")

def get_audit_logs():
	"""Get all audit logs"""
	try:
		if os.path.exists(AUDIT_LOG_FILE):
			with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
				return json.load(f)
	except Exception as e:
		print(f"Error reading audit logs: {e}")
	return []

def get_aircraft_logs(aircraft_id: str):
	"""Get logs for specific aircraft"""
	all_logs = get_audit_logs()
	return [log for log in all_logs if log['aircraft_id'] == aircraft_id]

# Load or initialize aircraft data
def load_aircraft_data():
	if os.path.exists(AIRCRAFT_FILE):
		try:
			with open(AIRCRAFT_FILE, 'r', encoding='utf-8') as f:
				data = json.load(f)
				aircraft_list = []
				for item in data:
					aircraft_list.append(Aircraft(
						aircraft_id=item['aircraft_id'],
						name=item['name'],
						status=MaintenanceStatus[item['status']],
						maintenance_date=date.fromisoformat(item['maintenance_date']),
						engineer_name=item['engineer_name']
					))
				return aircraft_list
		except Exception as e:
			print(f"Error loading aircraft data: {e}")
			return get_default_aircraft()
	else:
		return get_default_aircraft()

def get_default_aircraft():
	return [
		Aircraft("AC-101", "Boeing 737-800", MaintenanceStatus.SCHEDULED, date(2026, 9, 12), "Ava Patel"),
		Aircraft("AC-202", "Airbus A320neo", MaintenanceStatus.IN_PROGRESS, date(2026, 9, 9), "Liam Chen"),
		Aircraft("AC-303", "Boeing 787-9", MaintenanceStatus.COMPLETED, date(2026, 9, 8), "Mia Rodriguez"),
	]

def save_aircraft_data(records):
	"""Save aircraft data to JSON file"""
	try:
		with open(AIRCRAFT_FILE, 'w', encoding='utf-8') as f:
			data = []
			for aircraft in records:
				data.append({
					'aircraft_id': aircraft.aircraft_id,
					'name': aircraft.name,
					'status': aircraft.status.name,
					'maintenance_date': aircraft.maintenance_date.isoformat(),
					'engineer_name': aircraft.engineer_name
				})
			json.dump(data, f, indent=2)
	except Exception as e:
		print(f"Error saving aircraft data: {e}")

aircraft_records = load_aircraft_data()


def display_aircraft(records: list[Aircraft]) -> None:
	print("\nAircraft Maintenance Tracker")
	print("=" * 105)
	print(f"{'Aircraft ID':<15}{'Aircraft Name':<22}{'Status':<16}{'Maintenance Date':<20}{'Engineer'}")
	print("-" * 105)

	for aircraft in records:
		print(
			f"{aircraft.aircraft_id:<15}"
			f"{aircraft.name:<22}"
			f"{aircraft.status.value:<16}"
			f"{aircraft.maintenance_date:%Y-%m-%d}"
			f"{'':<10}{aircraft.engineer_name}"
		)


def run_tracker() -> None:
	while True:
		display_aircraft(aircraft_records)
		print("\nRefreshing every 5 seconds. Press Ctrl+C to stop.")
		time.sleep(5)


# Flask Routes
@app.route('/health', methods=['GET'])
def health():
	"""Health check endpoint"""
	return jsonify({
		'status': 'success',
		'message': 'App runs successfully',
		'service': 'Aircraft Maintenance Tracker'
	}), 200


@app.route('/')
def home():
	"""Serve the HTML page"""
	with open('index.html', 'r', encoding='utf-8') as f:
		return f.read()


@app.route('/api/aircraft', methods=['GET'])
def get_aircraft():
	"""API endpoint to get aircraft data as JSON"""
	aircraft_data = []
	for aircraft in aircraft_records:
		aircraft_data.append({
			'aircraft_id': aircraft.aircraft_id,
			'name': aircraft.name,
			'status': aircraft.status.value,
			'maintenance_date': aircraft.maintenance_date.strftime('%Y-%m-%d'),
			'engineer_name': aircraft.engineer_name
		})
	return jsonify(aircraft_data)


@app.route('/api/aircraft', methods=['POST'])
def add_aircraft():
	"""Add a new aircraft"""
	try:
		data = request.get_json()
		
		# Validate required fields
		required_fields = ['aircraft_id', 'name', 'maintenance_date', 'engineer_name']
		if not all(k in data for k in required_fields):
			missing = [k for k in required_fields if k not in data]
			return jsonify({
				'status': 'error',
				'error': f'Missing required fields: {", ".join(missing)}'
			}), 400
		
		# Validate Aircraft ID format
		aircraft_id = data['aircraft_id'].strip()
		if not aircraft_id or len(aircraft_id) < 3:
			return jsonify({
				'status': 'error',
				'error': 'Aircraft ID must be at least 3 characters long'
			}), 400
		
		# Check if aircraft_id already exists (uniqueness validation)
		if any(a.aircraft_id == aircraft_id for a in aircraft_records):
			return jsonify({
				'status': 'error',
				'error': f'Aircraft ID "{aircraft_id}" already exists. Please use a unique ID.'
			}), 409
		
		# Validate date format
		try:
			maint_date = date.fromisoformat(data['maintenance_date'])
		except (ValueError, TypeError):
			return jsonify({
				'status': 'error',
				'error': 'Invalid maintenance date format. Use YYYY-MM-DD'
			}), 400
		
		# Validate name and engineer
		if not data['name'].strip() or not data['engineer_name'].strip():
			return jsonify({
				'status': 'error',
				'error': 'Aircraft name and engineer name cannot be empty'
			}), 400
		
		# Create new aircraft with default status SCHEDULED
		new_aircraft = Aircraft(
			aircraft_id=aircraft_id,
			name=data['name'].strip(),
			status=MaintenanceStatus.SCHEDULED,
			maintenance_date=maint_date,
			engineer_name=data['engineer_name'].strip()
		)
		
		aircraft_records.append(new_aircraft)
		save_aircraft_data(aircraft_records)
		
		# Log this action
		add_audit_log('AIRCRAFT_REGISTERED', aircraft_id, {
			'name': new_aircraft.name,
			'initial_status': new_aircraft.status.value,
			'maintenance_date': new_aircraft.maintenance_date.isoformat(),
			'engineer': new_aircraft.engineer_name
		})
		
		return jsonify({
			'status': 'success',
			'message': 'Aircraft added successfully',
			'aircraft': {
				'aircraft_id': new_aircraft.aircraft_id,
				'name': new_aircraft.name,
				'status': new_aircraft.status.value,
				'maintenance_date': new_aircraft.maintenance_date.strftime('%Y-%m-%d'),
				'engineer_name': new_aircraft.engineer_name
			}
		}), 201
	except json.JSONDecodeError:
		return jsonify({
			'status': 'error',
			'error': 'Invalid JSON format'
		}), 400
	except Exception as e:
		return jsonify({
			'status': 'error',
			'error': f'Unexpected error: {str(e)}'
		}), 500


@app.route('/api/aircraft/<aircraft_id>/status', methods=['PUT'])
def update_status(aircraft_id):
	"""Update aircraft maintenance status - follows order: Scheduled -> In Progress -> Completed"""
	try:
		# Validate aircraft_id format
		if not aircraft_id or len(aircraft_id.strip()) == 0:
			return jsonify({
				'status': 'error',
				'error': 'Invalid aircraft ID'
			}), 400
		
		aircraft_id = aircraft_id.strip()
		
		# Find the aircraft
		aircraft = next((a for a in aircraft_records if a.aircraft_id == aircraft_id), None)
		if not aircraft:
			return jsonify({
				'status': 'error',
				'error': f'Aircraft with ID "{aircraft_id}" not found'
			}), 404
		
		# Get the next status
		next_status = MaintenanceStatus.get_next_status(aircraft.status)
		if next_status is None:
			return jsonify({
				'status': 'error',
				'error': f'Cannot update status. Aircraft "{aircraft_id}" is already at final status (Completed)',
				'current_status': aircraft.status.value
			}), 400
		
		# Update status
		old_status = aircraft.status.value
		aircraft.status = next_status
		save_aircraft_data(aircraft_records)
		
		# Log this status change
		add_audit_log('STATUS_UPDATED', aircraft_id, {
			'previous_status': old_status,
			'new_status': aircraft.status.value,
			'aircraft_name': aircraft.name,
			'engineer': aircraft.engineer_name
		})
		
		return jsonify({
			'status': 'success',
			'message': f'Status updated successfully',
			'aircraft_id': aircraft_id,
			'aircraft_name': aircraft.name,
			'old_status': old_status,
			'new_status': aircraft.status.value
		}), 200
	except Exception as e:
		return jsonify({
			'status': 'error',
			'error': f'Error updating status: {str(e)}'
		}), 500


@app.route('/api/aircraft/<aircraft_id>', methods=['DELETE'])
def delete_aircraft(aircraft_id):
	"""Delete an aircraft"""
	global aircraft_records
	try:
		# Validate aircraft_id format
		if not aircraft_id or len(aircraft_id.strip()) == 0:
			return jsonify({
				'status': 'error',
				'error': 'Invalid aircraft ID'
			}), 400
		
		aircraft_id = aircraft_id.strip()
		
		# Find the aircraft
		aircraft = next((a for a in aircraft_records if a.aircraft_id == aircraft_id), None)
		if not aircraft:
			return jsonify({
				'status': 'error',
				'error': f'Aircraft with ID "{aircraft_id}" not found'
			}), 404
		
		# Store info before deletion for logging
		deleted_aircraft = {
			'aircraft_id': aircraft.aircraft_id,
			'name': aircraft.name,
			'status': aircraft.status.value,
			'engineer': aircraft.engineer_name
		}
		
		# Delete the aircraft
		aircraft_records = [a for a in aircraft_records if a.aircraft_id != aircraft_id]
		save_aircraft_data(aircraft_records)
		
		# Log this action
		add_audit_log('AIRCRAFT_DELETED', aircraft_id, deleted_aircraft)
		
		return jsonify({
			'status': 'success',
			'message': f'Aircraft "{aircraft_id}" deleted successfully'
		}), 200
	except Exception as e:
		return jsonify({
			'status': 'error',
			'error': f'Error deleting aircraft: {str(e)}'
		}), 500


@app.route('/api/aircraft/active', methods=['GET'])
def get_active_aircraft():
	"""Get all aircraft currently in maintenance (In Progress status)"""
	try:
		active_aircraft = [
			{
				'aircraft_id': a.aircraft_id,
				'name': a.name,
				'status': a.status.value,
				'maintenance_date': a.maintenance_date.strftime('%Y-%m-%d'),
				'engineer_name': a.engineer_name
			}
			for a in aircraft_records if a.status == MaintenanceStatus.IN_PROGRESS
		]
		
		return jsonify({
			'status': 'success',
			'count': len(active_aircraft),
			'aircraft': active_aircraft
		}), 200
	except Exception as e:
		return jsonify({
			'status': 'error',
			'error': f'Error fetching active aircraft: {str(e)}'
		}), 500


@app.route('/api/aircraft/scheduled-today', methods=['GET'])
def get_scheduled_today():
	"""Get aircraft scheduled for maintenance today"""
	try:
		today = date.today()
		scheduled_today = [
			{
				'aircraft_id': a.aircraft_id,
				'name': a.name,
				'status': a.status.value,
				'maintenance_date': a.maintenance_date.strftime('%Y-%m-%d'),
				'engineer_name': a.engineer_name
			}
			for a in aircraft_records if a.maintenance_date == today
		]
		
		return jsonify({
			'status': 'success',
			'count': len(scheduled_today),
			'date': today.isoformat(),
			'aircraft': scheduled_today
		}), 200
	except Exception as e:
		return jsonify({
			'status': 'error',
			'error': f'Error fetching scheduled aircraft: {str(e)}'
		}), 500


@app.route('/api/logs', methods=['GET'])
def get_logs():
	"""Get all audit logs with optional filtering"""
	try:
		logs = get_audit_logs()
		
		# Optional: filter by action type
		action = request.args.get('action')
		if action:
			logs = [log for log in logs if log['action'] == action]
		
		# Optional: filter by aircraft_id
		aircraft_id = request.args.get('aircraft_id')
		if aircraft_id:
			logs = [log for log in logs if log['aircraft_id'] == aircraft_id]
		
		return jsonify({
			'status': 'success',
			'count': len(logs),
			'logs': logs
		}), 200
	except Exception as e:
		return jsonify({
			'status': 'error',
			'error': f'Error fetching logs: {str(e)}'
		}), 500


@app.route('/api/logs/<aircraft_id>', methods=['GET'])
def get_aircraft_history(aircraft_id):
	"""Get history/logs for a specific aircraft"""
	try:
		# Validate aircraft exists
		aircraft = next((a for a in aircraft_records if a.aircraft_id == aircraft_id), None)
		if not aircraft:
			return jsonify({
				'status': 'error',
				'error': f'Aircraft with ID "{aircraft_id}" not found'
			}), 404
		
		logs = get_aircraft_logs(aircraft_id)
		
		return jsonify({
			'status': 'success',
			'aircraft_id': aircraft_id,
			'aircraft_name': aircraft.name,
			'count': len(logs),
			'logs': logs
		}), 200
	except Exception as e:
		return jsonify({
			'status': 'error',
			'error': f'Error fetching aircraft history: {str(e)}'
		}), 500


@app.route('/api/stats', methods=['GET'])
def get_statistics():
	"""Get maintenance statistics"""
	try:
		total = len(aircraft_records)
		scheduled = len([a for a in aircraft_records if a.status == MaintenanceStatus.SCHEDULED])
		in_progress = len([a for a in aircraft_records if a.status == MaintenanceStatus.IN_PROGRESS])
		completed = len([a for a in aircraft_records if a.status == MaintenanceStatus.COMPLETED])
		
		logs = get_audit_logs()
		status_changes = len([log for log in logs if log['action'] == 'STATUS_UPDATED'])
		
		return jsonify({
			'status': 'success',
			'statistics': {
				'total_aircraft': total,
				'scheduled': scheduled,
				'in_progress': in_progress,
				'completed': completed,
				'total_status_changes': status_changes,
				'total_log_entries': len(logs)
			}
		}), 200
	except Exception as e:
		return jsonify({
			'status': 'error',
			'error': f'Error fetching statistics: {str(e)}'
		}), 500


@app.route('/styles.css')
def serve_css():
	"""Serve CSS file"""
	with open('styles.css', 'r', encoding='utf-8') as f:
		return f.read(), 200, {'Content-Type': 'text/css'}


@app.route('/script.js')
def serve_js():
	"""Serve JavaScript file"""
	with open('script.js', 'r', encoding='utf-8') as f:
		return f.read(), 200, {'Content-Type': 'application/javascript'}


@app.errorhandler(404)
def handle_404(e):
	"""Return JSON for API routes so the frontend never parses an HTML error page"""
	if request.path.startswith('/api/'):
		return jsonify({
			'status': 'error',
			'error': f'Endpoint not found: {request.path}'
		}), 404
	return e


@app.errorhandler(405)
def handle_405(e):
	if request.path.startswith('/api/'):
		return jsonify({
			'status': 'error',
			'error': f'Method {request.method} not allowed for {request.path}'
		}), 405
	return e


@app.errorhandler(500)
def handle_500(e):
	if request.path.startswith('/api/'):
		return jsonify({
			'status': 'error',
			'error': 'Internal server error'
		}), 500
	return e


def is_port_in_use(port: int) -> bool:
	"""Windows lets Werkzeug re-bind an occupied port, so probe it with a real connection"""
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
		sock.settimeout(0.5)
		return sock.connect_ex(('127.0.0.1', port)) == 0


def find_free_port(start_port: int = 5000, attempts: int = 20) -> int:
	for port in range(start_port, start_port + attempts):
		if not is_port_in_use(port):
			return port
	raise RuntimeError(f'No free port found in range {start_port}-{start_port + attempts}')


if __name__ == "__main__":
    print("Starting Aircraft Maintenance Tracker...")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
	#port = find_free_port(5000)
	#if port != 5000:
		#print(f"WARNING: Port 5000 is already in use by another server.")
		#print(f"         Using port {port} instead to avoid serving stale code.")

	#print(f"Open your browser and go to: http://localhost:{port}")
	#print("Press Ctrl+C to stop the server.\n")
	#try:
		#app.run(debug=True, use_reloader=False, port=port)
	#except KeyboardInterrupt:
		#print("\nTracker stopped.")
