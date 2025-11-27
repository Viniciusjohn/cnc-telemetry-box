#!/usr/bin/env python3
"""
Test script for microservices architecture.
Tests telemetry and status microservices independently.
"""

import subprocess
import time
import requests
import threading
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def start_telemetry_service():
    """Start telemetry microservice."""
    print("🚀 Starting Telemetry Microservice...")
    try:
        import uvicorn
        from backend.app.microservices.telemetry_service import app as telemetry_app
        
        def run_telemetry():
            uvicorn.run(telemetry_app, host='127.0.0.1', port=8002, log_level='warning')
        
        telemetry_thread = threading.Thread(target=run_telemetry, daemon=True)
        telemetry_thread.start()
        time.sleep(2)
        
        # Test health
        response = requests.get('http://127.0.0.1:8002/health', timeout=5)
        if response.status_code == 200:
            print("✅ Telemetry service started successfully")
            return True
        else:
            print("❌ Telemetry service failed to start")
            return False
    except Exception as e:
        print(f"❌ Failed to start telemetry service: {e}")
        return False

def start_status_service():
    """Start status microservice."""
    print("🚀 Starting Status Microservice...")
    try:
        import uvicorn
        from backend.app.microservices.status_service import app as status_app
        
        def run_status():
            uvicorn.run(status_app, host='127.0.0.1', port=8003, log_level='warning')
        
        status_thread = threading.Thread(target=run_status, daemon=True)
        status_thread.start()
        time.sleep(2)
        
        # Test health
        response = requests.get('http://127.0.0.1:8003/health', timeout=5)
        if response.status_code == 200:
            print("✅ Status service started successfully")
            return True
        else:
            print("❌ Status service failed to start")
            return False
    except Exception as e:
        print(f"❌ Failed to start status service: {e}")
        return False

def setup_services():
    """Setup dependency injection and event bus."""
    print("⚙️  Setting up services...")
    try:
        from backend.app.dependency_injection import setup_dependency_injection
        from backend.app.message_queue import setup_message_queue
        from backend.app.event_bus import event_bus
        
        # Setup DI
        setup_dependency_injection()
        print("   ✅ Dependency injection configured")
        
        # Setup message queue (in-memory for testing)
        queue_manager = setup_message_queue()
        print("   ✅ Message queue configured")
        
        # Start event bus
        import asyncio
        asyncio.create_task(event_bus.start())
        print("   ✅ Event bus started")
        
        return True
    except Exception as e:
        print(f"❌ Failed to setup services: {e}")
        return False

def test_telemetry_service():
    """Test telemetry microservice endpoints."""
    print("\n📡 Testing Telemetry Service...")
    base_url = 'http://127.0.0.1:8002'
    
    tests = [
        {
            'name': 'Health Check',
            'url': f'{base_url}/health',
            'method': 'GET',
            'expected': 200
        },
        {
            'name': 'Stats',
            'url': f'{base_url}/stats',
            'method': 'GET',
            'expected': 200
        },
        {
            'name': 'Telemetry Ingestion',
            'url': f'{base_url}/telemetry/ingest',
            'method': 'POST',
            'data': {
                'machine_id': 'MICRO-001',
                'timestamp': '2025-01-01T10:00:00Z',
                'rpm': 3000,
                'feed_mm_min': 1000,
                'state': 'running'
            },
            'expected': 200
        },
        {
            'name': 'Batch Telemetry',
            'url': f'{base_url}/telemetry/batch',
            'method': 'POST',
            'data': [
                {
                    'machine_id': 'MICRO-002',
                    'timestamp': '2025-01-01T10:01:00Z',
                    'rpm': 1500,
                    'feed_mm_min': 500,
                    'state': 'stopped'
                },
                {
                    'machine_id': 'MICRO-003',
                    'timestamp': '2025-01-01T10:02:00Z',
                    'rpm': 0,
                    'feed_mm_min': 0,
                    'state': 'idle'
                }
            ],
            'expected': 200
        }
    ]
    
    results = []
    for test in tests:
        try:
            if test['method'] == 'POST':
                response = requests.post(test['url'], json=test['data'], timeout=5)
            else:
                response = requests.get(test['url'], timeout=5)
            
            status = "✅ PASS" if response.status_code == test['expected'] else "❌ FAIL"
            results.append((test['name'], status, response.status_code))
            
            print(f"   {test['name']}: {status} ({response.status_code})")
            
            if response.status_code == 200 and response.text:
                try:
                    data = response.json()
                    if 'service' in data:
                        print(f"      Service: {data['service']}")
                    if 'processed_count' in data:
                        print(f"      Processed: {data['processed_count']}")
                except:
                    pass
                    
        except Exception as e:
            results.append((test['name'], "❌ ERROR", 0))
            print(f"   {test['name']}: ❌ ERROR - {e}")
    
    return results

def test_status_service():
    """Test status microservice endpoints."""
    print("\n📊 Testing Status Service...")
    base_url = 'http://127.0.0.1:8003'
    
    # First, send some telemetry to populate status
    try:
        requests.post(
            'http://127.0.0.1:8002/telemetry/ingest',
            json={
                'machine_id': 'STATUS-TEST',
                'timestamp': '2025-01-01T10:00:00Z',
                'rpm': 3000,
                'feed_mm_min': 1000,
                'state': 'running'
            },
            timeout=5
        )
        time.sleep(1)  # Allow processing
    except:
        pass
    
    tests = [
        {
            'name': 'Health Check',
            'url': f'{base_url}/health',
            'method': 'GET',
            'expected': 200
        },
        {
            'name': 'Stats',
            'url': f'{base_url}/stats',
            'method': 'GET',
            'expected': 200
        },
        {
            'name': 'List Machines',
            'url': f'{base_url}/machines',
            'method': 'GET',
            'expected': 200
        },
        {
            'name': 'Get All Statuses',
            'url': f'{base_url}/machines/status',
            'method': 'GET',
            'expected': 200
        },
        {
            'name': 'Update Machine Status',
            'url': f'{base_url}/machines/STATUS-TEST/status',
            'method': 'POST',
            'data': {
                'rpm': 2500,
                'feed_mm_min': 800,
                'state': 'running',
                'mode': 'AUTOMATIC',
                'execution': 'EXECUTING'
            },
            'expected': 200
        },
        {
            'name': 'Get Individual Status',
            'url': f'{base_url}/machines/STATUS-TEST/status',
            'method': 'GET',
            'expected': 200
        }
    ]
    
    results = []
    for test in tests:
        try:
            if test['method'] == 'POST':
                response = requests.post(test['url'], json=test['data'], timeout=5)
            else:
                response = requests.get(test['url'], timeout=5)
            
            status = "✅ PASS" if response.status_code == test['expected'] else "❌ FAIL"
            results.append((test['name'], status, response.status_code))
            
            print(f"   {test['name']}: {status} ({response.status_code})")
            
            if response.status_code == 200 and response.text:
                try:
                    data = response.json()
                    if 'service' in data:
                        print(f"      Service: {data['service']}")
                    if 'machine_count' in data:
                        print(f"      Machines: {data['machine_count']}")
                    if 'success' in data:
                        print(f"      Success: {data['success']}")
                except:
                    pass
                    
        except Exception as e:
            results.append((test['name'], "❌ ERROR", 0))
            print(f"   {test['name']}: ❌ ERROR - {e}")
    
    return results

def test_service_communication():
    """Test communication between services."""
    print("\n🔄 Testing Service Communication...")
    
    try:
        # Send telemetry via telemetry service
        print("   1. Sending telemetry via Telemetry Service...")
        response = requests.post(
            'http://127.0.0.1:8002/telemetry/ingest',
            json={
                'machine_id': 'COMM-TEST',
                'timestamp': '2025-01-01T10:00:00Z',
                'rpm': 3000,
                'feed_mm_min': 1000,
                'state': 'running'
            },
            timeout=5
        )
        
        if response.status_code == 200:
            print("   ✅ Telemetry sent successfully")
            
            # Wait for processing
            time.sleep(2)
            
            # Check status service
            print("   2. Checking status in Status Service...")
            response = requests.get('http://127.0.0.1:8003/machines/COMM-TEST/status', timeout=5)
            
            if response.status_code == 200:
                status_data = response.json()
                if status_data.get('machine_id') == 'COMM-TEST':
                    print("   ✅ Status propagated to Status Service")
                    print(f"      State: {status_data.get('state', 'unknown')}")
                    print(f"      RPM: {status_data.get('rpm', 0)}")
                    return True
                else:
                    print("   ⚠️  Status found but machine ID mismatch")
            else:
                print(f"   ❌ Status check failed: {response.status_code}")
        else:
            print(f"   ❌ Telemetry send failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Communication test error: {e}")
    
    return False

def test_circuit_breaker():
    """Test circuit breaker functionality."""
    print("\n⚡ Testing Circuit Breaker...")
    
    try:
        # This would require a failing external service
        # For now, we'll test the circuit breaker health endpoint
        from backend.app.circuit_breaker import get_circuit_breaker
        
        breaker = get_circuit_breaker("test-service")
        health = breaker.get_health()
        
        print(f"   ✅ Circuit breaker created")
        print(f"      Service: {health['service']}")
        print(f"      State: {health['state']}")
        print(f"      Failures: {health['failure_count']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Circuit breaker test error: {e}")
        return False

def test_event_bus():
    """Test event bus functionality."""
    print("\n📢 Testing Event Bus...")
    
    try:
        from backend.app.event_bus import event_bus, TelemetryReceived
        import asyncio
        
        # Create test event
        event = TelemetryReceived(
            machine_id="EVENT-TEST",
            rpm=3000,
            feed_mm_min=1000,
            state="running",
            timestamp_utc="2025-01-01T10:00:00Z"
        )
        
        # Publish event
        asyncio.run(event_bus.publish(event))
        print("   ✅ Event published successfully")
        
        # Get stats
        stats = event_bus.get_stats()
        print(f"      Events published: {stats['events_published']}")
        print(f"      Handlers registered: {stats['handlers_registered']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Event bus test error: {e}")
        return False

def main():
    """Run microservices integration tests."""
    print("🎯 CNC Telemetry Box - Microservices Test Suite")
    print("=" * 60)
    
    # Setup services
    if not setup_services():
        print("❌ Service setup failed - aborting tests")
        return
    
    # Start microservices
    telemetry_ok = start_telemetry_service()
    status_ok = start_status_service()
    
    if not telemetry_ok or not status_ok:
        print("❌ Microservices startup failed - aborting tests")
        return
    
    try:
        # Run tests
        telemetry_results = test_telemetry_service()
        status_results = test_status_service()
        
        communication_ok = test_service_communication()
        circuit_ok = test_circuit_breaker()
        event_ok = test_event_bus()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 MICROSERVICES TEST SUMMARY")
        print("=" * 60)
        
        # Telemetry service results
        telemetry_passed = sum(1 for _, status, _ in telemetry_results if "PASS" in status)
        telemetry_total = len(telemetry_results)
        print(f"Telemetry Service: {telemetry_passed}/{telemetry_total} tests passed")
        
        # Status service results
        status_passed = sum(1 for _, status, _ in status_results if "PASS" in status)
        status_total = len(status_results)
        print(f"Status Service: {status_passed}/{status_total} tests passed")
        
        # Integration tests
        print("\nIntegration Tests:")
        print(f"   Service Communication: {'✅ PASS' if communication_ok else '❌ FAIL'}")
        print(f"   Circuit Breaker: {'✅ PASS' if circuit_ok else '❌ FAIL'}")
        print(f"   Event Bus: {'✅ PASS' if event_ok else '❌ FAIL'}")
        
        # Overall
        total_passed = telemetry_passed + status_passed + (1 if communication_ok else 0) + (1 if circuit_ok else 0) + (1 if event_ok else 0)
        total_tests = telemetry_total + status_total + 3
        
        success_rate = (total_passed / total_tests) * 100
        print(f"\n🏆 Overall Success Rate: {success_rate:.1f}% ({total_passed}/{total_tests})")
        
        if success_rate >= 80:
            print("🎉 Microservices architecture is working well!")
        elif success_rate >= 60:
            print("⚠️  Microservices working but need attention")
        else:
            print("❌ Microservices need significant fixes")
        
    finally:
        print("\n🧹 Test completed - microservices will shut down automatically")

if __name__ == '__main__':
    main()
