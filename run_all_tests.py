#!/usr/bin/env python3
"""
Master test runner for CNC Telemetry Box.
Runs all test suites and provides comprehensive reporting.
"""

import subprocess
import sys
import time
import json
from pathlib import Path
from datetime import datetime

def run_test_script(script_name, description):
    """Run a test script and return results."""
    print(f"\n{'='*60}")
    print(f"🧪 Running: {description}")
    print(f"📁 Script: {script_name}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        success = result.returncode == 0
        
        print(f"\n📊 Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        
        if result.stdout:
            print(f"\n📋 Output:")
            print(result.stdout)
        
        if result.stderr:
            print(f"\n⚠️  Errors:")
            print(result.stderr)
        
        return {
            'script': script_name,
            'description': description,
            'success': success,
            'duration': duration,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
        
    except subprocess.TimeoutExpired:
        print(f"\n⏰ TIMEOUT: {script_name} took too long to run")
        return {
            'script': script_name,
            'description': description,
            'success': False,
            'duration': 300,
            'stdout': '',
            'stderr': 'Test timed out after 5 minutes',
            'returncode': -1
        }
    
    except Exception as e:
        print(f"\n💥 ERROR: Failed to run {script_name}: {e}")
        return {
            'script': script_name,
            'description': description,
            'success': False,
            'duration': 0,
            'stdout': '',
            'stderr': str(e),
            'returncode': -2
        }

def check_prerequisites():
    """Check if all prerequisites are met."""
    print("🔍 Checking prerequisites...")
    
    issues = []
    
    # Check Python version
    if sys.version_info < (3, 8):
        issues.append("Python 3.8+ required")
    
    # Check if backend directory exists
    if not Path("backend").exists():
        issues.append("Backend directory not found")
    
    # Check if frontend directory exists
    if not Path("frontend").exists():
        issues.append("Frontend directory not found")
    
    # Check if requirements.txt exists
    if not Path("backend/requirements.txt").exists():
        issues.append("Backend requirements.txt not found")
    
    if issues:
        print("❌ Prerequisites failed:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    
    print("✅ All prerequisites met")
    return True


def ensure_backend_dependencies():
    """Ensure backend Python dependencies are installed."""
    requirements_file = Path("backend/requirements.txt")
    if not requirements_file.exists():
        return True

    required_modules = [
        "structlog",
        "pythonjsonlogger",
        "slowapi",
    ]

    missing = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)

    if not missing:
        return True

    print("\n📦 Installing backend dependencies (missing: " + ", ".join(missing) + ")")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("❌ Failed to install dependencies:")
        print(result.stderr)
        return False

    print("✅ Backend dependencies installed")
    return True

def generate_report(results):
    """Generate comprehensive test report."""
    print("\n" + "="*80)
    print("📊 COMPREHENSIVE TEST REPORT")
    print("="*80)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['success'])
    failed_tests = total_tests - passed_tests
    total_duration = sum(r['duration'] for r in results)
    
    print(f"\n📈 SUMMARY:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {passed_tests} ✅")
    print(f"   Failed: {failed_tests} ❌")
    print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    print(f"   Total Duration: {total_duration:.2f} seconds")
    
    print(f"\n📋 DETAILED RESULTS:")
    for i, result in enumerate(results, 1):
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"   {i}. {result['description']}: {status} ({result['duration']:.1f}s)")
    
    if failed_tests > 0:
        print(f"\n❌ FAILED TESTS:")
        for result in results:
            if not result['success']:
                print(f"\n   📁 {result['script']}")
                print(f"   📝 {result['description']}")
                if result['stderr']:
                    print(f"   ⚠️  {result['stderr'][:200]}...")
    
    # Save report to file
    report_data = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'success_rate': (passed_tests/total_tests)*100,
            'duration': total_duration
        },
        'results': results
    }
    
    report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"\n💾 Report saved to: {report_file}")
    
    # Overall assessment
    if failed_tests == 0:
        print(f"\n🎉 ALL TESTS PASSED! System is ready for production.")
    elif passed_tests >= failed_tests:
        print(f"\n⚠️  Some tests failed. Review and fix issues before deployment.")
    else:
        print(f"\n❌ Multiple test failures. System needs significant fixes.")
    
    return failed_tests == 0

def main():
    """Run all test suites."""
    print("🎯 CNC Telemetry Box - Master Test Runner")
    print("=" * 80)
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Aborting tests.")
        return False

    if not ensure_backend_dependencies():
        print("\n❌ Could not ensure backend dependencies. Aborting tests.")
        return False
    
    # Define test suites
    test_suites = [
        {
            'script': 'test_multi_machine.py',
            'description': 'Multi-Machine Backend Functionality'
        },
        {
            'script': 'test_frontend_integration.py',
            'description': 'Frontend Components Integration'
        },
        {
            'script': 'test_microservices.py',
            'description': 'Microservices Architecture'
        }
    ]
    
    # Run all tests
    results = []
    start_time = time.time()
    
    for suite in test_suites:
        if Path(suite['script']).exists():
            result = run_test_script(suite['script'], suite['description'])
            results.append(result)
        else:
            print(f"\n⚠️  Test script not found: {suite['script']}")
            results.append({
                'script': suite['script'],
                'description': suite['description'],
                'success': False,
                'duration': 0,
                'stdout': '',
                'stderr': 'Test script not found',
                'returncode': -3
            })
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\n⏱️  Total test execution time: {total_time:.2f} seconds")
    
    # Generate report
    success = generate_report(results)
    
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
