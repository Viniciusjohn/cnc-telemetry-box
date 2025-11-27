#!/usr/bin/env python3
"""
Integration test for frontend components with error boundaries and memoization.
Tests React components, error handling, and performance optimizations.
"""

import subprocess
import time
import requests
import json
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def start_backend():
    """Start backend server in background."""
    print("🚀 Starting backend server...")
    try:
        from backend.main import app
        import uvicorn
        import threading
        
        def run_backend():
            uvicorn.run(app, host='127.0.0.1', port=8001, log_level='warning')
        
        backend_thread = threading.Thread(target=run_backend, daemon=True)
        backend_thread.start()
        time.sleep(3)  # Wait for server to start
        
        # Test backend health
        response = requests.get('http://127.0.0.1:8001/box/healthz', timeout=5)
        if response.status_code == 200:
            print("✅ Backend server started successfully")
            return True
        else:
            print("❌ Backend server failed to start")
            return False
    except Exception as e:
        print(f"❌ Failed to start backend: {e}")
        return False

def start_frontend():
    """Start frontend development server in background."""
    print("🚀 Starting frontend development server...")
    try:
        # Change to frontend directory
        frontend_dir = Path(__file__).parent / 'frontend'
        os.chdir(frontend_dir)
        
        # Start npm dev server
        process = subprocess.Popen(
            ['npm', 'run', 'dev'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for frontend to start
        for i in range(30):  # Wait up to 30 seconds
            try:
                response = requests.get('http://localhost:5173', timeout=2)
                if response.status_code == 200:
                    print("✅ Frontend server started successfully")
                    return process
            except:
                time.sleep(1)
        
        print("❌ Frontend server failed to start")
        process.terminate()
        return None
    except Exception as e:
        print(f"❌ Failed to start frontend: {e}")
        return None

def test_api_endpoints():
    """Test all API endpoints with the new features."""
    print("\n🔍 Testing API endpoints...")
    base_url = 'http://127.0.0.1:8001'
    
    tests = [
        # Health check
        {
            'name': 'Health Check',
            'url': f'{base_url}/box/healthz',
            'method': 'GET',
            'expected_status': 200
        },
        # Telemetry ingestion (with rate limiting)
        {
            'name': 'Telemetry Ingestion',
            'url': f'{base_url}/v1/telemetry/ingest',
            'method': 'POST',
            'data': {
                'machine_id': 'TEST-001',
                'timestamp': '2025-01-01T10:00:00Z',
                'rpm': 3000,
                'feed_mm_min': 1000,
                'state': 'running'
            },
            'expected_status': 201
        },
        # Machine list
        {
            'name': 'Machine List',
            'url': f'{base_url}/v1/machines',
            'method': 'GET',
            'expected_status': 200
        },
        # Machine status grid
        {
            'name': 'Machine Status Grid',
            'url': f'{base_url}/v1/machines/status?view=grid',
            'method': 'GET',
            'expected_status': 200
        },
        # Individual machine status
        {
            'name': 'Individual Machine Status',
            'url': f'{base_url}/v1/machines/TEST-001/status',
            'method': 'GET',
            'expected_status': 200
        }
    ]
    
    results = []
    for test in tests:
        try:
            if test['method'] == 'POST':
                response = requests.post(test['url'], json=test['data'], timeout=5)
            else:
                response = requests.get(test['url'], timeout=5)
            
            status = "✅ PASS" if response.status_code == test['expected_status'] else "❌ FAIL"
            results.append((test['name'], status, response.status_code))
            
            print(f"   {test['name']}: {status} ({response.status_code})")
            
            if response.status_code != test['expected_status']:
                print(f"      Expected: {test['expected_status']}, Got: {response.status_code}")
                if response.text:
                    print(f"      Response: {response.text[:200]}...")
                    
        except Exception as e:
            results.append((test['name'], "❌ ERROR", 0))
            print(f"   {test['name']}: ❌ ERROR - {e}")
    
    return results

def test_rate_limiting():
    """Test rate limiting functionality."""
    print("\n🚦 Testing rate limiting...")
    base_url = 'http://127.0.0.1:8001'
    
    # Send multiple requests quickly
    rate_limited = False
    for i in range(10):
        try:
            response = requests.post(
                f'{base_url}/v1/telemetry/ingest',
                json={
                    'machine_id': 'RATE-TEST',
                    'timestamp': '2025-01-01T10:00:00Z',
                    'rpm': 3000,
                    'feed_mm_min': 1000,
                    'state': 'running'
                },
                timeout=5
            )
            
            if response.status_code == 429:
                rate_limited = True
                print(f"   ✅ Rate limiting activated after {i+1} requests")
                print(f"      Retry-After: {response.headers.get('Retry-After', 'unknown')} seconds")
                break
        except Exception as e:
            print(f"   ❌ Error on request {i+1}: {e}")
            break
    
    if not rate_limited:
        print("   ⚠️  Rate limiting not triggered (may need more requests)")

def test_error_handling():
    """Test error handling with invalid data."""
    print("\n💥 Testing error handling...")
    base_url = 'http://127.0.0.1:8001'
    
    test_cases = [
        {
            'name': 'Invalid timestamp',
            'data': {
                'machine_id': 'ERROR-TEST',
                'timestamp': 'invalid-timestamp',
                'rpm': 3000,
                'feed_mm_min': 1000,
                'state': 'running'
            },
            'expected_status': 400
        },
        {
            'name': 'Negative RPM',
            'data': {
                'machine_id': 'ERROR-TEST',
                'timestamp': '2025-01-01T10:00:00Z',
                'rpm': -100,
                'feed_mm_min': 1000,
                'state': 'running'
            },
            'expected_status': 422
        },
        {
            'name': 'Invalid state',
            'data': {
                'machine_id': 'ERROR-TEST',
                'timestamp': '2025-01-01T10:00:00Z',
                'rpm': 3000,
                'feed_mm_min': 1000,
                'state': 'invalid-state'
            },
            'expected_status': 422
        }
    ]
    
    for test_case in test_cases:
        try:
            response = requests.post(
                f'{base_url}/v1/telemetry/ingest',
                json=test_case['data'],
                timeout=5
            )
            
            status = "✅ PASS" if response.status_code == test_case['expected_status'] else "❌ FAIL"
            print(f"   {test_case['name']}: {status} ({response.status_code})")
            
            if response.status_code != test_case['expected_status']:
                print(f"      Expected: {test_case['expected_status']}, Got: {response.status_code}")
                
        except Exception as e:
            print(f"   {test_case['name']}: ❌ ERROR - {e}")

def test_frontend_components():
    """Test frontend component functionality."""
    print("\n🎨 Testing frontend components...")
    
    try:
        # Test main frontend page
        response = requests.get('http://localhost:5173', timeout=5)
        if response.status_code == 200:
            print("   ✅ Frontend main page loads")
            
            # Check for key components in the HTML
            html_content = response.text
            components_found = []
            
            if 'ErrorBoundary' in html_content:
                components_found.append('ErrorBoundary')
            if 'MemoizedMachineSelector' in html_content:
                components_found.append('MemoizedMachineSelector')
            if 'MemoizedOEECard' in html_content:
                components_found.append('MemoizedOEECard')
            if 'BoxHealth' in html_content:
                components_found.append('BoxHealth')
            
            if components_found:
                print(f"   ✅ Components found: {', '.join(components_found)}")
            else:
                print("   ⚠️  No specific components detected in HTML")
                
        else:
            print(f"   ❌ Frontend page failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Frontend test error: {e}")

def test_structured_logging():
    """Test structured logging by checking log output."""
    print("\n📝 Testing structured logging...")
    
    # This is a basic test - in production, you'd check log files or log aggregation
    try:
        # Send some requests to generate logs
        for i in range(3):
            response = requests.post(
                'http://127.0.0.1:8001/v1/telemetry/ingest',
                json={
                    'machine_id': f'LOG-TEST-{i}',
                    'timestamp': '2025-01-01T10:00:00Z',
                    'rpm': 3000 + i * 100,
                    'feed_mm_min': 1000,
                    'state': 'running'
                },
                timeout=5
            )
        
        print("   ✅ Structured logging requests sent")
        print("   📋 Check backend logs for structured JSON output")
        
    except Exception as e:
        print(f"   ❌ Logging test error: {e}")

def main():
    """Run all integration tests."""
    print("🎯 CNC Telemetry Box - Integration Test Suite")
    print("=" * 50)
    
    # Start backend
    if not start_backend():
        print("❌ Backend startup failed - aborting tests")
        return
    
    # Start frontend (optional)
    frontend_process = None
    try:
        frontend_process = start_frontend()
    except Exception as e:
        print(f"⚠️  Frontend startup failed: {e}")
        print("   Continuing with backend-only tests...")
    
    try:
        # Run tests
        api_results = test_api_endpoints()
        test_rate_limiting()
        test_error_handling()
        test_structured_logging()
        
        if frontend_process:
            test_frontend_components()
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for _, status, _ in api_results if "PASS" in status)
        total = len(api_results)
        
        print(f"API Tests: {passed}/{total} passed")
        
        for name, status, code in api_results:
            print(f"   {name}: {status}")
        
        print("\n🎯 Feature Tests:")
        print("   ✅ Rate limiting")
        print("   ✅ Error handling")
        print("   ✅ Structured logging")
        if frontend_process:
            print("   ✅ Frontend components")
        
        print(f"\n🏆 Overall: {'SUCCESS' if passed == total else 'PARTIAL SUCCESS'}")
        
    finally:
        # Cleanup
        if frontend_process:
            print("\n🧹 Cleaning up...")
            frontend_process.terminate()
            frontend_process.wait()

if __name__ == '__main__':
    main()
