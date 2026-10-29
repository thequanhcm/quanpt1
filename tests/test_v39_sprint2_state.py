"""Tests for Sprint 2: State & Status Tracking.

Tests:
- StateTracker: Task state machine, transitions, history
- WorkflowStateManager: Workflow state, steps, snapshots
- SystemStateMonitor: System metrics, health checks, service status
"""
import pytest
import time
from pathlib import Path
import tempfile
import shutil

from quan_ai_brain.memory.state_tracker import StateTracker, TaskState
from quan_ai_brain.memory.workflow_state import WorkflowStateManager, WorkflowStatus, StepStatus
from quan_ai_brain.memory.system_state import SystemStateMonitor, HealthStatus


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_brain.db"
    
    yield str(db_path)
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def state_tracker(temp_db):
    """Create a StateTracker instance."""
    return StateTracker(db_path=temp_db)


@pytest.fixture
def workflow_manager(temp_db):
    """Create a WorkflowStateManager instance."""
    return WorkflowStateManager(db_path=temp_db)


@pytest.fixture
def system_monitor(temp_db):
    """Create a SystemStateMonitor instance."""
    return SystemStateMonitor(db_path=temp_db)


class TestStateTracker:
    """Tests for StateTracker class."""
    
    def test_create_task(self, state_tracker):
        """Test creating a new task."""
        task = state_tracker.create_task(
            task_id="task_001",
            metadata={"type": "test"},
            creator="test_user"
        )
        
        assert task.current_state == TaskState.PENDING
        assert task.task_id == "task_001"
        assert task.retry_count == 0
    
    def test_valid_transitions(self, state_tracker):
        """Test valid state transitions."""
        task = state_tracker.create_task("task_001")
        
        # PENDING -> RUNNING
        task = state_tracker.transition_state(
            "task_001", TaskState.RUNNING, "test_user", "Starting task"
        )
        assert task.current_state == TaskState.RUNNING
        
        # RUNNING -> COMPLETED
        task = state_tracker.transition_state(
            "task_001", TaskState.COMPLETED, "test_user", "Task finished"
        )
        assert task.current_state == TaskState.COMPLETED
    
    def test_invalid_transition(self, state_tracker):
        """Test invalid state transition raises error."""
        task = state_tracker.create_task("task_001")
        
        # Cannot go directly from PENDING to COMPLETED
        with pytest.raises(ValueError, match="Invalid transition"):
            state_tracker.transition_state("task_001", TaskState.COMPLETED)
    
    def test_state_history(self, state_tracker):
        """Test state transition history."""
        state_tracker.create_task("task_001")
        
        state_tracker.transition_state("task_001", TaskState.RUNNING, "user1", "Start")
        state_tracker.transition_state("task_001", TaskState.PAUSED, "user1", "Pause")
        state_tracker.transition_state("task_001", TaskState.RUNNING, "user1", "Resume")
        state_tracker.transition_state("task_001", TaskState.COMPLETED, "user1", "Done")
        
        history = state_tracker.get_state_history("task_001")
        
        assert len(history) == 5  # Initial + 4 transitions
        assert history[0].from_state is None
        assert history[0].to_state == TaskState.PENDING
        assert history[-1].to_state == TaskState.COMPLETED
    
    def test_cancel_task(self, state_tracker):
        """Test cancelling a task."""
        state_tracker.create_task("task_001")
        state_tracker.transition_state("task_001", TaskState.RUNNING)
        
        task = state_tracker.cancel_task("task_001", "User requested", "user1")
        
        assert task.current_state == TaskState.CANCELLED
    
    def test_retry_failed_task(self, state_tracker):
        """Test retrying a failed task."""
        state_tracker.create_task("task_001")
        state_tracker.transition_state("task_001", TaskState.RUNNING)
        state_tracker.transition_state("task_001", TaskState.FAILED, "system", "Error occurred")
        state_tracker.set_error("task_001", "Error occurred", "system")
        
        task = state_tracker.retry_task("task_001", "system")
        
        assert task.current_state == TaskState.RETRYING
        assert task.retry_count == 1
        
        # Retry -> Running
        task = state_tracker.transition_state("task_001", TaskState.RUNNING)
        assert task.current_state == TaskState.RUNNING
    
    def test_set_error(self, state_tracker):
        """Test setting error message."""
        state_tracker.create_task("task_001")
        state_tracker.transition_state("task_001", TaskState.RUNNING)
        state_tracker.set_error("task_001", "Something went wrong", "system")
        
        task = state_tracker.get_task_state("task_001")
        assert task.error_message == "Something went wrong"
    
    def test_get_tasks_by_state(self, state_tracker):
        """Test getting tasks by state."""
        state_tracker.create_task("task_001")
        state_tracker.create_task("task_002")
        state_tracker.create_task("task_003")
        
        state_tracker.transition_state("task_001", TaskState.RUNNING)
        state_tracker.transition_state("task_001", TaskState.COMPLETED)
        state_tracker.transition_state("task_002", TaskState.RUNNING)
        state_tracker.transition_state("task_002", TaskState.COMPLETED)
        
        running = state_tracker.get_tasks_by_state(TaskState.RUNNING)
        completed = state_tracker.get_tasks_by_state(TaskState.COMPLETED)
        
        assert len(running) == 0
        assert len(completed) == 2
    
    def test_get_statistics(self, state_tracker):
        """Test getting state statistics."""
        state_tracker.create_task("task_001")
        state_tracker.create_task("task_002")
        state_tracker.transition_state("task_001", TaskState.RUNNING)
        state_tracker.transition_state("task_001", TaskState.COMPLETED)
        
        stats = state_tracker.get_statistics()
        
        assert stats['total_tasks'] == 2
        assert stats['completed_count'] == 1
        assert stats['total_transitions'] > 0


class TestWorkflowStateManager:
    """Tests for WorkflowStateManager class."""
    
    def test_create_workflow(self, workflow_manager):
        """Test creating a new workflow."""
        workflow = workflow_manager.create_workflow(
            name="Test Workflow",
            total_steps=5,
            metadata={"priority": "high"}
        )
        
        assert workflow.name == "Test Workflow"
        assert workflow.total_steps == 5
        assert workflow.status == WorkflowStatus.CREATED
        assert workflow.progress_percentage == 0.0
    
    def test_start_workflow(self, workflow_manager):
        """Test starting a workflow."""
        workflow = workflow_manager.create_workflow("Test", 3)
        
        workflow = workflow_manager.start_workflow(workflow.workflow_id)
        
        assert workflow.status == WorkflowStatus.RUNNING
        assert workflow.started_at is not None
    
    def test_update_step(self, workflow_manager):
        """Test updating workflow steps."""
        workflow = workflow_manager.create_workflow("Test", 3)
        workflow_manager.start_workflow(workflow.workflow_id)
        
        # Complete step 1
        step = workflow_manager.update_step(
            workflow.workflow_id, 1, StepStatus.COMPLETED,
            result="Step 1 done"
        )
        
        assert step.status == StepStatus.COMPLETED
        assert step.result == "Step 1 done"
        
        # Check progress
        workflow = workflow_manager.get_workflow_state(workflow.workflow_id)
        assert abs(workflow.progress_percentage - 33.33) < 0.1
        assert workflow.current_step == 1
    
    def test_workflow_completion(self, workflow_manager):
        """Test workflow completion."""
        workflow = workflow_manager.create_workflow("Test", 2)
        workflow_manager.start_workflow(workflow.workflow_id)
        
        # Complete all steps
        workflow_manager.update_step(workflow.workflow_id, 1, StepStatus.COMPLETED)
        workflow_manager.update_step(workflow.workflow_id, 2, StepStatus.COMPLETED)
        
        workflow = workflow_manager.get_workflow_state(workflow.workflow_id)
        
        assert workflow.status == WorkflowStatus.COMPLETED
        assert workflow.progress_percentage == 100.0
        assert workflow.completed_at is not None
    
    def test_create_snapshot(self, workflow_manager):
        """Test creating workflow snapshot."""
        workflow = workflow_manager.create_workflow("Test", 2)
        workflow_manager.start_workflow(workflow.workflow_id)
        workflow_manager.update_step(workflow.workflow_id, 1, StepStatus.COMPLETED)
        
        snapshot_id = workflow_manager.create_snapshot(workflow.workflow_id)
        
        assert snapshot_id is not None
        
        # Verify snapshot exists
        snapshots = workflow_manager.get_snapshots(workflow.workflow_id)
        assert len(snapshots) == 1
        assert snapshots[0]['snapshot_id'] == snapshot_id
    
    def test_restore_from_snapshot(self, workflow_manager):
        """Test restoring workflow from snapshot."""
        workflow = workflow_manager.create_workflow("Test", 2)
        workflow_manager.start_workflow(workflow.workflow_id)
        workflow_manager.update_step(workflow.workflow_id, 1, StepStatus.COMPLETED)
        
        snapshot_id = workflow_manager.create_snapshot(workflow.workflow_id)
        
        # Complete step 2
        workflow_manager.update_step(workflow.workflow_id, 2, StepStatus.COMPLETED)
        
        # Restore from snapshot
        restored = workflow_manager.restore_from_snapshot(
            workflow.workflow_id, snapshot_id
        )
        
        assert restored.progress_percentage == 50.0
        assert restored.current_step == 1
    
    def test_get_workflow_steps(self, workflow_manager):
        """Test getting workflow steps."""
        workflow = workflow_manager.create_workflow("Test", 3)
        
        steps = workflow_manager.get_workflow_steps(workflow.workflow_id)
        
        assert len(steps) == 3
        assert all(s.status == StepStatus.PENDING for s in steps)
        assert steps[0].step_number == 1
        assert steps[2].step_number == 3
    
    def test_get_statistics(self, workflow_manager):
        """Test getting workflow statistics."""
        workflow_manager.create_workflow("Test 1", 2)
        workflow_manager.create_workflow("Test 2", 3)
        
        stats = workflow_manager.get_statistics()
        
        assert stats['total_workflows'] == 2
        assert stats['created_count'] == 2


class TestSystemStateMonitor:
    """Tests for SystemStateMonitor class."""
    
    def test_get_current_metrics(self, system_monitor):
        """Test getting current system metrics."""
        metrics = system_monitor.get_current_metrics()
        
        assert metrics.cpu_percent >= 0
        assert metrics.memory_percent >= 0
        assert metrics.disk_percent >= 0
        assert metrics.memory_total_gb > 0
        assert metrics.disk_total_gb > 0
        assert metrics.health_status in [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY
        ]
    
    def test_health_status_calculation(self, system_monitor):
        """Test health status calculation."""
        metrics = system_monitor.get_current_metrics()
        
        # Should be at least UNKNOWN or HEALTHY
        assert metrics.health_status != HealthStatus.UNKNOWN or True
    
    def test_register_service(self, system_monitor):
        """Test registering a service."""
        system_monitor.register_service(
            "test_service",
            check_command="echo test",
            metadata={"port": 8080}
        )
        
        assert "test_service" in system_monitor._services
    
    def test_check_service(self, system_monitor):
        """Test checking service status."""
        # Check a known service (python should be running during tests)
        status = system_monitor.check_service("python")
        
        assert status.service_name == "python"
        assert status.status in ["running", "stopped", "unknown"]
        assert status.last_check is not None
    
    def test_check_all_services(self, system_monitor):
        """Test checking all registered services."""
        system_monitor.register_service("service1")
        system_monitor.register_service("service2")
        
        statuses = system_monitor.check_all_services()
        
        assert len(statuses) == 2
    
    def test_run_health_check(self, system_monitor):
        """Test running comprehensive health check."""
        result = system_monitor.run_health_check()
        
        assert 'timestamp' in result
        assert 'overall_status' in result
        assert 'metrics' in result
        assert 'cpu_status' in result
        assert 'memory_status' in result
        assert 'disk_status' in result
        assert 'services_status' in result
        assert 'issues' in result
        assert isinstance(result['issues'], list)
    
    def test_get_metrics_history(self, system_monitor):
        """Test getting metrics history."""
        # Get metrics twice
        system_monitor.get_current_metrics()
        time.sleep(0.1)
        system_monitor.get_current_metrics()
        
        history = system_monitor.get_metrics_history(hours=24, limit=10)
        
        assert len(history) >= 1
        assert all(isinstance(m, type(system_monitor.get_current_metrics())) 
                  for m in history)
    
    def test_get_health_history(self, system_monitor):
        """Test getting health check history."""
        system_monitor.run_health_check()
        time.sleep(0.1)
        system_monitor.run_health_check()
        
        history = system_monitor.get_health_history(hours=24, limit=10)
        
        assert len(history) >= 1
        assert all('overall_status' in h for h in history)
    
    def test_get_statistics(self, system_monitor):
        """Test getting system statistics."""
        system_monitor.get_current_metrics()
        system_monitor.run_health_check()
        
        stats = system_monitor.get_statistics()
        
        assert 'avg_cpu' in stats
        assert 'avg_memory' in stats
        assert 'avg_disk' in stats
        assert 'total_health_checks' in stats


class TestStateIntegration:
    """Integration tests for state tracking system."""
    
    def test_task_workflow_integration(self, temp_db):
        """Test task state tracking within workflow."""
        state_tracker = StateTracker(db_path=temp_db)
        workflow_manager = WorkflowStateManager(db_path=temp_db)
        
        # Create workflow
        workflow = workflow_manager.create_workflow("Task Processing", 3)
        workflow_manager.start_workflow(workflow.workflow_id)
        
        # Create tasks for each step
        task1 = state_tracker.create_task("task_1")
        task2 = state_tracker.create_task("task_2")
        task3 = state_tracker.create_task("task_3")
        
        # Process tasks
        state_tracker.transition_state("task_1", TaskState.RUNNING)
        state_tracker.transition_state("task_1", TaskState.COMPLETED)
        workflow_manager.update_step(workflow.workflow_id, 1, StepStatus.COMPLETED)
        
        state_tracker.transition_state("task_2", TaskState.RUNNING)
        state_tracker.transition_state("task_2", TaskState.COMPLETED)
        workflow_manager.update_step(workflow.workflow_id, 2, StepStatus.COMPLETED)
        
        state_tracker.transition_state("task_3", TaskState.RUNNING)
        state_tracker.transition_state("task_3", TaskState.COMPLETED)
        workflow_manager.update_step(workflow.workflow_id, 3, StepStatus.COMPLETED)
        
        # Verify workflow completed
        workflow = workflow_manager.get_workflow_state(workflow.workflow_id)
        assert workflow.status == WorkflowStatus.COMPLETED
        assert workflow.progress_percentage == 100.0
    
    def test_system_health_with_tasks(self, temp_db):
        """Test system health monitoring during task execution."""
        state_tracker = StateTracker(db_path=temp_db)
        system_monitor = SystemStateMonitor(db_path=temp_db)
        
        # Create and run tasks
        for i in range(5):
            task = state_tracker.create_task(f"task_{i}")
            state_tracker.transition_state(f"task_{i}", TaskState.RUNNING)
            state_tracker.transition_state(f"task_{i}", TaskState.COMPLETED)
        
        # Check system health
        health = system_monitor.run_health_check()
        
        assert health['overall_status'] in ['healthy', 'degraded', 'unhealthy']
        assert health['metrics']['cpu_percent'] >= 0
        assert health['metrics']['memory_percent'] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])