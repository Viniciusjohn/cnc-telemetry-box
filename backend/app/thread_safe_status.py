"""
Thread-safe status storage for CNC Telemetry Box.
Replace global dictionary with thread-safe implementation.
"""

import threading
import time
from datetime import datetime, timezone
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import copy

from ..routers.status import MachineStatus

@dataclass
class StatusEntry:
    """Thread-safe wrapper for machine status with metadata."""
    status: MachineStatus
    last_updated: datetime
    update_count: int
    lock: threading.RLock
    
    def __post_init__(self):
        if isinstance(self.last_updated, str):
            self.last_updated = datetime.fromisoformat(self.last_updated.replace('Z', '+00:00'))
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON response."""
        result = asdict(self.status)
        result['last_updated'] = self.last_updated.isoformat().replace('+00:00', 'Z')
        result['update_count'] = self.update_count
        return result

class ThreadSafeStatusManager:
    """Thread-safe manager for machine status storage."""
    
    def __init__(self):
        self._statuses: Dict[str, StatusEntry] = {}
        self._global_lock = threading.RLock()
        self._stats = {
            'total_updates': 0,
            'total_reads': 0,
            'last_cleanup': time.time()
        }
        self._cleanup_interval = 300  # 5 minutes
    
    @contextmanager
    def _machine_lock(self, machine_id: str):
        """Context manager for machine-specific lock."""
        with self._global_lock:
            if machine_id not in self._statuses:
                # Create new entry with lock
                self._statuses[machine_id] = StatusEntry(
                    status=MachineStatus(
                        machine_id=machine_id,
                        rpm=0.0,
                        feed_mm_min=0.0,
                        state="idle",
                        timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                        execution="READY",
                        mode="AUTOMATIC",
                        path_feedrate=0.0,
                        spindle_speed=0.0,
                        tool_id=None,
                        part_id=None,
                        operation=None,
                        controller_mode="AUTOMATIC",
                        alarm_code=None,
                        alarm_message=None
                    ),
                    last_updated=datetime.now(timezone.utc),
                    update_count=0,
                    lock=threading.RLock()
                )
            
            machine_entry = self._statuses[machine_id]
        
        # Acquire machine-specific lock
        with machine_entry.lock:
            yield machine_entry
    
    def update_status(self, machine_id: str, **kwargs) -> bool:
        """
        Update machine status thread-safely.
        
        Args:
            machine_id: Machine identifier
            **kwargs: Status fields to update
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            with self._machine_lock(machine_id) as entry:
                # Update status fields
                for key, value in kwargs.items():
                    if hasattr(entry.status, key):
                        setattr(entry.status, key, value)
                
                # Update metadata
                entry.status.timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                entry.last_updated = datetime.now(timezone.utc)
                entry.update_count += 1
                
                # Update global stats
                with self._global_lock:
                    self._stats['total_updates'] += 1
                
                return True
                
        except Exception as e:
            print(f"Error updating status for {machine_id}: {e}")
            return False
    
    def get_status(self, machine_id: str) -> Optional[Dict]:
        """
        Get machine status thread-safely.
        
        Args:
            machine_id: Machine identifier
            
        Returns:
            Status dictionary or None if not found
        """
        try:
            with self._global_lock:
                if machine_id not in self._statuses:
                    return None
                
                entry = self._statuses[machine_id]
            
            # Read under machine lock
            with entry.lock:
                with self._global_lock:
                    self._stats['total_reads'] += 1
                
                # Return deep copy to avoid race conditions
                return copy.deepcopy(entry.to_dict())
                
        except Exception as e:
            print(f"Error getting status for {machine_id}: {e}")
            return None
    
    def get_all_statuses(self) -> List[Dict]:
        """
        Get all machine statuses thread-safely.
        
        Returns:
            List of status dictionaries
        """
        try:
            with self._global_lock:
                machine_ids = list(self._statuses.keys())
            
            results = []
            for machine_id in machine_ids:
                status = self.get_status(machine_id)
                if status:
                    results.append(status)
            
            return results
            
        except Exception as e:
            print(f"Error getting all statuses: {e}")
            return []
    
    def cleanup_old_entries(self, max_age_seconds: int = 3600) -> int:
        """
        Remove old entries to prevent memory leaks.
        
        Args:
            max_age_seconds: Maximum age in seconds
            
        Returns:
            Number of entries removed
        """
        current_time = time.time()
        
        with self._global_lock:
            if current_time - self._stats['last_cleanup'] < self._cleanup_interval:
                return 0
            
            cutoff_time = datetime.now(timezone.utc).timestamp() - max_age_seconds
            to_remove = []
            
            for machine_id, entry in self._statuses.items():
                if entry.last_updated.timestamp() < cutoff_time:
                    to_remove.append(machine_id)
            
            for machine_id in to_remove:
                del self._statuses[machine_id]
            
            self._stats['last_cleanup'] = current_time
            
            return len(to_remove)
    
    def get_stats(self) -> Dict:
        """Get manager statistics."""
        with self._global_lock:
            return {
                'machine_count': len(self._statuses),
                'total_updates': self._stats['total_updates'],
                'total_reads': self._stats['total_reads'],
                'last_cleanup': datetime.fromtimestamp(self._stats['last_cleanup']).isoformat(),
                'machines': list(self._statuses.keys())
            }
    
    def health_check(self) -> Dict:
        """Health check for the status manager."""
        try:
            stats = self.get_stats()
            
            # Test update/read cycle
            test_machine = "_health_check"
            test_success = self.update_status(test_machine, rpm=1000)
            if test_success:
                retrieved = self.get_status(test_machine)
                test_success = retrieved is not None and retrieved.get('rpm') == 1000
                # Clean up test entry
                with self._global_lock:
                    self._statuses.pop(test_machine, None)
            
            return {
                'status': 'healthy' if test_success else 'degraded',
                'stats': stats,
                'test_passed': test_success,
                'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }

# Global instance
status_manager = ThreadSafeStatusManager()

# Migration function from old LAST_STATUS
def migrate_from_legacy_status(legacy_status: Dict) -> int:
    """
    Migrate from legacy LAST_STATUS dictionary.
    
    Args:
        legacy_status: Old LAST_STATUS dictionary
        
    Returns:
        Number of entries migrated
    """
    migrated = 0
    
    for machine_id, machine_status in legacy_status.items():
        if isinstance(machine_status, dict):
            success = status_manager.update_status(machine_id, **machine_status)
            if success:
                migrated += 1
    
    return migrated
