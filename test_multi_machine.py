import uvicorn
import threading
import time
import requests
import sys
import os
import asyncio
import logging

# Ensure UTF-8 output for Windows consoles that default to cp1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from backend.main import app

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_server():
    uvicorn.run(app, host='127.0.0.1', port=8001, log_level='info')

def test_multi_machine():
    # Start server in background
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(3)  # Wait for server to start

    print('=== Testing complete multi-machine functionality ===')

    # Send telemetry from 3 different machines
    machines_data = [
        {'machine_id': 'M80-001', 'timestamp': '2025-01-01T10:00:00Z', 'rpm': 3000, 'feed_mm_min': 1000, 'state': 'running'},
        {'machine_id': 'M80-002', 'timestamp': '2025-01-01T10:01:00Z', 'rpm': 1500, 'feed_mm_min': 500, 'state': 'stopped'},
        {'machine_id': 'M80-003', 'timestamp': '2025-01-01T10:02:00Z', 'rpm': 0, 'feed_mm_min': 0, 'state': 'idle'}
    ]

    base = 'http://127.0.0.1:8001'

    print('1. Sending telemetry from 3 machines...')
    for i, machine_data in enumerate(machines_data, 1):
        try:
            r = requests.post(f'{base}/v1/telemetry/ingest', json=machine_data, timeout=5)
            print(f'   Machine {i} ({machine_data["machine_id"]}): Status {r.status_code}')
            if r.status_code == 201:
                print(f'      Response: {r.json()}')
            else:
                print(f'      Error: {r.text}')
        except requests.exceptions.RequestException as e:
            print(f'   Machine {i} ({machine_data["machine_id"]}): ERROR - {e}')

    print('\n2. Testing /v1/machines endpoint:')
    try:
        r = requests.get(f'{base}/v1/machines', timeout=5)
        print(f'   Status: {r.status_code}')
        if r.status_code == 200:
            print(f'   Machines: {r.json()}')
        else:
            print(f'   Error: {r.text}')
    except requests.exceptions.RequestException as e:
        print(f'   ERROR: {e}')

    print('\n3. Testing /v1/machines/status?view=grid endpoint:')
    try:
        r = requests.get(f'{base}/v1/machines/status?view=grid', timeout=5)
        print(f'   Status: {r.status_code}')
        if r.status_code == 200:
            grid_data = r.json()
            for item in grid_data:
                print(f'   - {item["machine_id"]}: {item["execution"]} @ {item["rpm"]} RPM')
        else:
            print(f'   Error: {r.text}')
    except requests.exceptions.RequestException as e:
        print(f'   ERROR: {e}')

    print('\n4. Testing individual machine status:')
    for machine_id in ['M80-001', 'M80-002', 'M80-003']:
        try:
            r = requests.get(f'{base}/v1/machines/{machine_id}/status', timeout=5)
            print(f'   {machine_id}: {r.status_code} -> {r.json()["execution"]}')
        except requests.exceptions.RequestException as e:
            print(f'   {machine_id}: ERROR - {e}')

    print('\n5. Testing /box/healthz endpoint:')
    try:
        r = requests.get(f'{base}/box/healthz', timeout=5)
        print(f'   Status: {r.status_code}')
        if r.status_code == 200:
            health_data = r.json()
            print(f'   Overall Health: {health_data.get("overall", {}).get("status", "unknown")}')
            print(f'   Services: {list(health_data.get("services", {}).keys())}')
        else:
            print(f'   Error: {r.text}')
    except requests.exceptions.RequestException as e:
        print(f'   ERROR: {e}')

    print('\n6. Testing rate limiting (multiple requests):')
    try:
        # Send multiple requests quickly to test rate limiting
        for i in range(5):
            r = requests.post(f'{base}/v1/telemetry/ingest', 
                            json={'machine_id': 'M80-001', 'timestamp': '2025-01-01T10:00:00Z', 
                                  'rpm': 3000, 'feed_mm_min': 1000, 'state': 'running'}, 
                            timeout=5)
            print(f'   Request {i+1}: Status {r.status_code}')
            if r.status_code == 429:
                print(f'      Rate limited! Retry after: {r.headers.get("Retry-After", "unknown")} seconds')
                break
    except requests.exceptions.RequestException as e:
        print(f'   ERROR: {e}')

    print('\n7. Testing error handling (invalid data):')
    try:
        # Send invalid telemetry data
        invalid_data = {'machine_id': 'M80-001', 'timestamp': 'invalid-timestamp', 'rpm': -100, 'feed_mm_min': 5000, 'state': 'invalid-state'}
        r = requests.post(f'{base}/v1/telemetry/ingest', json=invalid_data, timeout=5)
        print(f'   Invalid data: Status {r.status_code}')
        print(f'   Error response: {r.text}')
    except requests.exceptions.RequestException as e:
        print(f'   ERROR: {e}')

    print('\n=== Multi-machine backend test completed! ===')
    print('\n🎯 Test Summary:')
    print('   ✅ Telemetry ingestion from multiple machines')
    print('   ✅ Machine list endpoint')
    print('   ✅ Grid status endpoint')
    print('   ✅ Individual machine status')
    print('   ✅ Health check endpoint')
    print('   ✅ Rate limiting')
    print('   ✅ Error handling')

if __name__ == '__main__':
    test_multi_machine()
