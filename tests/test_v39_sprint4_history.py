"""Tests for Sprint 4: Enhanced Task History.

Tests:
- TaskJournalManager: Create journals, add actions, complete tasks
- ActionLogger: Track actions, context manager, patterns
- MetricsTracker: Record metrics, statistics, trends
"""
import pytest
import time
from pathlib import Path
import tempfile
import shutil

from quan_ai_brain.memory.task_journal import (
    TaskJournalManager, TaskJournal, TaskAction,
    ActionStatus, ActionType
)
from quan_ai_brain.memory.action_logger import ActionLogger
from quan_ai_brain.memory.metrics_tracker import MetricsTracker


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_brain.db"
    
    yield str(db_path)
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def journal_manager(temp_db):
    """Create a TaskJournalManager instance."""
    return TaskJournalManager(db_path=temp_db)


@pytest.fixture
def action_logger(temp_db):
    """Create an ActionLogger instance."""
    return ActionLogger(db_path=temp_db)


@pytest.fixture
def metrics_tracker(temp_db):
    """Create a MetricsTracker instance."""
    return MetricsTracker(db_path=temp_db)


class TestTaskJournalManager:
    """Tests for TaskJournalManager class."""
    
    def test_create_journal(self, journal_manager):
        """Test creating a new task journal."""
        journal = journal_manager.create_journal(
            task_id="task_001",
            title="Test Task",
            description="Testing task journal",
            metadata={"priority": "high"}
        )
        
        assert journal.task_id == "task_001"
        assert journal.title == "Test Task"
        assert journal.status == "pending"
        assert journal.total_actions == 0
    
    def test_start_task(self, journal_manager):
        """Test starting a task."""
        journal_manager.create_journal("task_001", "Test", "Test description")
        
        journal = journal_manager.start_task("task_001")
        
        assert journal.status == "running"
        assert journal.started_at is not None
    
    def test_add_action(self, journal_manager):
        """Test adding actions to journal."""
        journal_manager.create_journal("task_001", "Test", "Test")
        
        action = journal_manager.add_action(
            task_id="task_001",
            action_type=ActionType.COMPUTE,
            name="Calculate",
            description="Perform calculation",
            input_data={"value": 42}
        )
        
        assert action.action_number == 1
        assert action.action_type == ActionType.COMPUTE
        assert action.status == ActionStatus.PENDING
        
        # Check journal updated
        journal = journal_manager.get_journal("task_001")
        assert journal.total_actions == 1
    
    def test_complete_action(self, journal_manager):
        """Test completing an action."""
        journal_manager.create_journal("task_001", "Test", "Test")
        
        action = journal_manager.add_action(
            task_id="task_001",
            action_type=ActionType.COMPUTE,
            name="Calculate",
            description="Test calculation"
        )
        
        time.sleep(0.01)  # Small delay to ensure duration > 0
        journal_manager.complete_action(
            action.id,
            output_data={"result": 84}
        )
        
        # Check action updated
        actions = journal_manager.get_actions("task_001")
        assert len(actions) == 1
        assert actions[0].status == ActionStatus.COMPLETED
        assert actions[0].duration_ms is not None
        assert actions[0].duration_ms >= 0
    
    def test_complete_action_with_error(self, journal_manager):
        """Test completing action with error."""
        journal_manager.create_journal("task_001", "Test", "Test")
        
        action = journal_manager.add_action(
            task_id="task_001",
            action_type=ActionType.VALIDATION,
            name="Validate",
            description="Test validation"
        )
        
        journal_manager.complete_action(
            action.id,
            error_message="Validation failed"
        )
        
        actions = journal_manager.get_actions("task_001")
        assert actions[0].status == ActionStatus.FAILED
        assert actions[0].error_message == "Validation failed"
        
        # Check journal stats
        journal = journal_manager.get_journal("task_001")
        assert journal.failed_actions == 1
    
    def test_complete_task(self, journal_manager):
        """Test completing a task."""
        journal_manager.create_journal("task_001", "Test", "Test")
        journal_manager.start_task("task_001")
        
        action = journal_manager.add_action(
            task_id="task_001",
            action_type=ActionType.COMPUTE,
            name="Process",
            description="Test process"
        )
        journal_manager.complete_action(action.id, output_data={"done": True})
        
        journal_manager.complete_task("task_001", result="Success")
        
        journal = journal_manager.get_journal("task_001")
        assert journal.status == "completed"
        assert journal.completed_at is not None
        assert journal.result == "Success"
    
    def test_complete_task_with_error(self, journal_manager):
        """Test completing task with error."""
        journal_manager.create_journal("task_001", "Test", "Test")
        
        journal_manager.complete_task("task_001", error_message="Task failed")
        
        journal = journal_manager.get_journal("task_001")
        assert journal.status == "failed"
        assert journal.error_message == "Task failed"
    
    def test_get_timeline(self, journal_manager):
        """Test getting execution timeline."""
        journal_manager.create_journal("task_001", "Test", "Test")
        
        action1 = journal_manager.add_action(
            task_id="task_001",
            action_type=ActionType.DATA_READ,
            name="Read data",
            description="Read input data"
        )
        journal_manager.complete_action(action1.id)
        
        action2 = journal_manager.add_action(
            task_id="task_001",
            action_type=ActionType.COMPUTE,
            name="Process",
            description="Process data"
        )
        journal_manager.complete_action(action2.id)
        
        timeline = journal_manager.get_timeline("task_001")
        
        assert len(timeline) == 2
        assert timeline[0]['name'] == "Read data"
        assert timeline[1]['name'] == "Process"
        assert timeline[0]['action_number'] == 1
        assert timeline[1]['action_number'] == 2
    
    def test_search_journals(self, journal_manager):
        """Test searching task journals."""
        journal_manager.create_journal("task_001", "Task 1", "Test")
        journal_manager.create_journal("task_002", "Task 2", "Test")
        journal_manager.create_journal("task_003", "Task 3", "Test")
        
        journal_manager.complete_task("task_001", result="Success")
        journal_manager.complete_task("task_002", error_message="Failed")
        
        completed = journal_manager.search_journals(status="completed")
        failed = journal_manager.search_journals(status="failed")
        
        assert len(completed) == 1
        assert len(failed) == 1
        assert completed[0].task_id == "task_001"
    
    def test_get_statistics(self, journal_manager):
        """Test getting journal statistics."""
        journal_manager.create_journal("task_001", "Task 1", "Test")
        journal_manager.create_journal("task_002", "Task 2", "Test")
        journal_manager.create_journal("task_003", "Task 3", "Test")
        
        journal_manager.complete_task("task_001", result="Success")
        journal_manager.complete_task("task_002", result="Success")
        journal_manager.complete_task("task_003", error_message="Failed")
        
        stats = journal_manager.get_statistics()
        
        assert stats['total_journals'] == 3
        assert stats['by_status']['completed'] == 2
        assert stats['by_status']['failed'] == 1
        assert stats['success_rate'] > 60


class TestActionLogger:
    """Tests for ActionLogger class."""
    
    def test_log_action(self, action_logger):
        """Test logging action start."""
        journal_manager = action_logger.journal_manager
        journal_manager.create_journal("task_001", "Test", "Test")
        
        action_id = action_logger.log_action(
            task_id="task_001",
            action_type=ActionType.COMPUTE,
            name="Calculate",
            input_data={"x": 10}
        )
        
        assert action_id is not None
        assert action_id in action_logger._active_actions
    
    def test_complete_action(self, action_logger):
        """Test completing logged action."""
        journal_manager = action_logger.journal_manager
        journal_manager.create_journal("task_001", "Test", "Test")
        
        action_id = action_logger.log_action(
            task_id="task_001",
            action_type=ActionType.COMPUTE,
            name="Calculate"
        )
        
        time.sleep(0.01)
        action_logger.complete_action(
            action_id,
            output_data={"result": 100}
        )
        
        assert action_id not in action_logger._active_actions
    
    def test_track_action_context_manager(self, action_logger):
        """Test context manager for action tracking."""
        journal_manager = action_logger.journal_manager
        journal_manager.create_journal("task_001", "Test", "Test")
        
        with action_logger.track_action(
            task_id="task_001",
            action_type=ActionType.COMPUTE,
            name="Process"
        ) as action_id:
            # Do some work
            result = 42
        
        # Action should be completed
        actions = journal_manager.get_actions("task_001")
        assert len(actions) == 1
        assert actions[0].status == ActionStatus.COMPLETED
    
    def test_track_action_with_error(self, action_logger):
        """Test context manager with error."""
        journal_manager = action_logger.journal_manager
        journal_manager.create_journal("task_001", "Test", "Test")
        
        with pytest.raises(ValueError):
            with action_logger.track_action(
                task_id="task_001",
                action_type=ActionType.VALIDATION,
                name="Validate"
            ):
                raise ValueError("Validation failed")
        
        # Action should be marked as failed
        actions = journal_manager.get_actions("task_001")
        assert actions[0].status == ActionStatus.FAILED
    
    def test_log_function_call(self, action_logger):
        """Test logging function call."""
        journal_manager = action_logger.journal_manager
        journal_manager.create_journal("task_001", "Test", "Test")
        
        def add(a, b):
            return a + b
        
        # Use context manager instead
        with action_logger.track_action(
            task_id="task_001",
            action_type=ActionType.COMPUTE,
            name="Add numbers",
            input_data={"a": 5, "b": 3}
        ) as action_id:
            result = add(5, 3)
        
        assert result == 8
        
        actions = journal_manager.get_actions("task_001")
        assert len(actions) == 1
        assert actions[0].status == ActionStatus.COMPLETED
    
    def test_analyze_action_patterns(self, action_logger):
        """Test analyzing action patterns."""
        journal_manager = action_logger.journal_manager
        journal_manager.create_journal("task_001", "Test", "Test")
        
        # Add multiple actions
        for i in range(5):
            action = journal_manager.add_action(
                task_id="task_001",
                action_type=ActionType.COMPUTE,
                name=f"Compute {i}",
                description=f"Compute iteration {i}"
            )
            journal_manager.complete_action(action.id)
        
        patterns = action_logger.analyze_action_patterns("task_001")
        
        assert patterns['total_actions'] == 5
        assert patterns['by_type']['compute'] == 5
        assert patterns['by_status']['completed'] == 5
        assert patterns['error_rate'] == 0


class TestMetricsTracker:
    """Tests for MetricsTracker class."""
    
    def test_record_metric(self, metrics_tracker):
        """Test recording a metric."""
        metric_id = metrics_tracker.record_metric(
            task_id="task_001",
            metric_name="execution_time",
            metric_value=150.5,
            unit="ms"
        )
        
        assert metric_id is not None
        
        metrics = metrics_tracker.get_metrics("task_001")
        assert len(metrics) == 1
        assert metrics[0].metric_value == 150.5
    
    def test_record_task_metrics(self, metrics_tracker):
        """Test recording aggregated task metrics."""
        metrics_tracker.record_task_metrics(
            task_id="task_001",
            total_duration_ms=1500,
            actions_count=10,
            success_rate=90.0,
            avg_action_duration_ms=150,
            error_count=1,
            memory_peak_mb=256.5,
            cpu_avg_percent=45.2
        )
        
        summary = metrics_tracker.get_task_metrics_summary("task_001")
        
        assert summary is not None
        assert summary.total_duration_ms == 1500
        assert summary.success_rate == 90.0
        assert summary.memory_peak_mb == 256.5
    
    def test_get_metrics(self, metrics_tracker):
        """Test getting metrics for task."""
        metrics_tracker.record_metric("task_001", "cpu_usage", 45.5, "%")
        metrics_tracker.record_metric("task_001", "memory_usage", 512, "MB")
        metrics_tracker.record_metric("task_001", "cpu_usage", 50.2, "%")
        
        all_metrics = metrics_tracker.get_metrics("task_001")
        cpu_metrics = metrics_tracker.get_metrics("task_001", "cpu_usage")
        
        assert len(all_metrics) == 3
        assert len(cpu_metrics) == 2
    
    def test_get_metric_statistics(self, metrics_tracker):
        """Test getting metric statistics."""
        for i in range(5):
            metrics_tracker.record_metric(
                "task_001",
                "response_time",
                100 + i * 10,
                "ms"
            )
        
        stats = metrics_tracker.get_metric_statistics("response_time")
        
        assert stats['count'] == 5
        assert stats['avg_value'] == 120
        assert stats['min_value'] == 100
        assert stats['max_value'] == 140
    
    def test_get_trend(self, metrics_tracker):
        """Test getting metric trend."""
        for i in range(10):
            metrics_tracker.record_metric(
                "task_001",
                "throughput",
                100 + i * 5,
                "req/s"
            )
            time.sleep(0.01)
        
        trend = metrics_tracker.get_trend("throughput")
        
        assert len(trend) > 0
        assert all('time' in t and 'avg_value' in t for t in trend)
    
    def test_compare_tasks(self, metrics_tracker):
        """Test comparing tasks."""
        metrics_tracker.record_task_metrics(
            "task_001", 1000, 10, 95.0, 100, 0,
            quality_score=0.9
        )
        metrics_tracker.record_task_metrics(
            "task_002", 1500, 15, 90.0, 100, 1,
            quality_score=0.8
        )
        
        comparison = metrics_tracker.compare_tasks(["task_001", "task_002"])
        
        assert len(comparison['tasks']) == 2
        assert comparison['best_by_metric']['fastest'] == "task_001"
        assert comparison['best_by_metric']['best_success_rate'] == "task_001"
        assert comparison['best_by_metric']['best_quality'] == "task_001"
    
    def test_get_statistics(self, metrics_tracker):
        """Test getting overall statistics."""
        metrics_tracker.record_metric("task_001", "metric1", 100, "unit")
        metrics_tracker.record_metric("task_002", "metric2", 200, "unit")
        metrics_tracker.record_task_metrics(
            "task_001", 1000, 5, 100.0, 200, 0
        )
        metrics_tracker.record_task_metrics(
            "task_002", 1500, 10, 90.0, 150, 1
        )
        
        stats = metrics_tracker.get_statistics()
        
        assert stats['total_metrics'] == 2
        assert stats['unique_metrics'] == 2
        assert stats['total_tasks_tracked'] == 2
        assert stats['avg_success_rate'] > 90


class TestTaskHistoryIntegration:
    """Integration tests for task history system."""
    
    def test_full_task_lifecycle(self, temp_db):
        """Test complete task lifecycle with all components."""
        journal_manager = TaskJournalManager(db_path=temp_db)
        action_logger = ActionLogger(db_path=temp_db)
        metrics_tracker = MetricsTracker(db_path=temp_db)
        
        # Create task
        journal_manager.create_journal("task_001", "Data Processing", "Process data")
        journal_manager.start_task("task_001")
        
        # Execute actions
        action1 = journal_manager.add_action(
            "task_001", ActionType.DATA_READ, "Read input", "Read input data"
        )
        journal_manager.complete_action(action1.id, output_data={"rows": 1000})
        metrics_tracker.record_metric("task_001", "data_read", 1000, "rows")
        
        action2 = journal_manager.add_action(
            "task_001", ActionType.COMPUTE, "Transform", "Transform data"
        )
        journal_manager.complete_action(action2.id, output_data={"transformed": True})
        metrics_tracker.record_metric("task_001", "compute_time", 150, "ms")
        
        action3 = journal_manager.add_action(
            "task_001", ActionType.DATA_WRITE, "Write output", "Write output data"
        )
        journal_manager.complete_action(action3.id, output_data={"written": True})
        metrics_tracker.record_metric("task_001", "data_written", 500, "rows")
        
        # Complete task
        journal_manager.complete_task("task_001", result="Success")
        
        # Record final metrics
        journal = journal_manager.get_journal("task_001")
        metrics_tracker.record_task_metrics(
            "task_001",
            total_duration_ms=journal.total_duration_ms,
            actions_count=journal.total_actions,
            success_rate=100.0,
            avg_action_duration_ms=journal.total_duration_ms / 3,
            error_count=0
        )
        
        # Verify
        assert journal.status == "completed"
        assert journal.total_actions == 3
        assert journal.successful_actions == 3
        
        summary = metrics_tracker.get_task_metrics_summary("task_001")
        assert summary is not None
        assert summary.success_rate == 100.0
    
    def test_failed_task_tracking(self, temp_db):
        """Test tracking failed task."""
        journal_manager = TaskJournalManager(db_path=temp_db)
        metrics_tracker = MetricsTracker(db_path=temp_db)
        
        journal_manager.create_journal("task_002", "Failing Task", "Test failure")
        journal_manager.start_task("task_002")
        
        action1 = journal_manager.add_action(
            "task_002", ActionType.COMPUTE, "Process", "Process data"
        )
        journal_manager.complete_action(
            action1.id, error_message="Division by zero"
        )
        
        journal_manager.complete_task("task_002", error_message="Task failed")
        
        journal = journal_manager.get_journal("task_002")
        assert journal.status == "failed"
        assert journal.failed_actions == 1
        
        metrics_tracker.record_task_metrics(
            "task_002",
            total_duration_ms=journal.total_duration_ms,
            actions_count=1,
            success_rate=0.0,
            avg_action_duration_ms=0,
            error_count=1
        )
        
        summary = metrics_tracker.get_task_metrics_summary("task_002")
        assert summary.success_rate == 0.0
        assert summary.error_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])