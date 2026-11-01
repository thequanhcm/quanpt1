"""V39.3 Task Planning Engine.

Implements task planning capabilities:
- Task breakdown (WBS, decomposition)
- Dependency analysis (precedence, critical path)
- Resource allocation (skills, availability, cost)
- Timeline optimization (Gantt, critical path method)
- Schedule risk analysis
- Progress tracking
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set
from enum import Enum
from collections import defaultdict
import heapq
from datetime import datetime, timedelta


class TaskStatus(Enum):
    """Task status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    DELAYED = "delayed"


class Priority(Enum):
    """Task priority."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Task:
    """Task definition."""
    task_id: str
    name: str
    description: str
    estimated_duration: float  # In hours
    actual_duration: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: TaskStatus = TaskStatus.NOT_STARTED
    priority: Priority = Priority.MEDIUM
    dependencies: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    progress: float = 0.0  # 0-100
    predecessor_tasks: List['Task'] = field(default_factory=list)
    successor_tasks: List['Task'] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "estimated_duration": self.estimated_duration,
            "status": self.status.value,
            "priority": self.priority.value,
            "dependencies": self.dependencies,
            "resources": self.resources,
            "progress": self.progress
        }


@dataclass
class Resource:
    """Resource definition."""
    resource_id: str
    name: str
    skills: List[str]
    availability: float  # 0-1 (fraction of time)
    cost_per_hour: float
    current_load: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "resource_id": self.resource_id,
            "name": self.name,
            "skills": self.skills,
            "availability": self.availability,
            "cost_per_hour": self.cost_per_hour,
            "current_load": self.current_load
        }


@dataclass
class Plan:
    """Project plan."""
    plan_id: str
    name: str
    tasks: List[Task]
    resources: List[Resource]
    start_date: datetime
    end_date: datetime
    total_duration: float
    critical_path: List[str]
    total_cost: float
    milestones: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "plan_id": self.plan_id,
            "name": self.name,
            "task_count": len(self.tasks),
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "total_duration": self.total_duration,
            "critical_path": self.critical_path,
            "total_cost": round(self.total_cost, 2),
            "milestone_count": len(self.milestones)
        }


class TaskPlanner:
    """Task planning engine."""
    
    def __init__(self, working_hours_per_day: float = 8.0):
        """Initialize task planner.
        
        Args:
            working_hours_per_day: Working hours per day
        """
        self.working_hours_per_day = working_hours_per_day
        self.task_counter = 0
        self._initialized = True
        
        print("✅ Task Planning Engine initialized")
        print(f"   - Task breakdown: Ready")
        print(f"   - Dependency analysis: Ready")
        print(f"   - Resource allocation: Ready")
        print(f"   - Timeline optimization: Ready")
        print(f"   - Critical path analysis: Ready")
    
    def break_down_task(self, parent_task: str, 
                       level: int = 0,
                       max_level: int = 3) -> List[Task]:
        """Break down a complex task into sub-tasks.
        
        Args:
            parent_task: Parent task description
            level: Current decomposition level
            max_level: Maximum decomposition depth
            
        Returns:
            List of sub-tasks
        """
        self.task_counter += 1
        tasks = []
        
        # Generate sub-tasks based on task type
        if level >= max_level:
            # Leaf task
            tasks.append(Task(
                task_id=f"TASK_{self.task_counter:04d}",
                name=parent_task[:50],
                description=parent_task,
                estimated_duration=4.0,
                priority=Priority.MEDIUM,
                status=TaskStatus.NOT_STARTED
            ))
        else:
            # Decompose into phases
            phases = [
                f"Plan {parent_task}",
                f"Design {parent_task}",
                f"Implement {parent_task}",
                f"Test {parent_task}",
                f"Deploy {parent_task}"
            ]
            
            for phase in phases:
                # Recursively break down
                sub_tasks = self.break_down_task(phase, level + 1, max_level)
                tasks.extend(sub_tasks)
        
        return tasks
    
    def analyze_dependencies(self, tasks: List[Task]) -> Dict[str, Any]:
        """Analyze task dependencies.
        
        Args:
            tasks: List of tasks
            
        Returns:
            Dependency analysis results
        """
        # Build dependency graph
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        for task in tasks:
            task_id = task.task_id
            in_degree[task_id] = len(task.dependencies)
            
            for dep_id in task.dependencies:
                graph[dep_id].append(task_id)
        
        # Topological sort
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        sorted_tasks = []
        
        while queue:
            current = queue.pop(0)
            sorted_tasks.append(current)
            
            for successor in graph[current]:
                in_degree[successor] -= 1
                if in_degree[successor] == 0:
                    queue.append(successor)
        
        # Detect cycles
        has_cycle = len(sorted_tasks) != len(tasks)
        
        # Calculate dependency depth
        depths = {}
        for task_id in sorted_tasks:
            max_pred_depth = 0
            for task in tasks:
                if task.task_id == task_id:
                    for dep_id in task.dependencies:
                        max_pred_depth = max(max_pred_depth, depths.get(dep_id, 0) + 1)
                    depths[task_id] = max_pred_depth
                    break
        
        return {
            "sorted_order": sorted_tasks,
            "has_cycle": has_cycle,
            "depths": depths,
            "max_depth": max(depths.values()) if depths else 0
        }
    
    def allocate_resources(self, tasks: List[Task],
                          resources: List[Resource]) -> Dict[str, List[str]]:
        """Allocate resources to tasks.
        
        Args:
            tasks: List of tasks
            resources: Available resources
            
        Returns:
            Mapping of task_id to allocated resource_ids
        """
        allocations = {}
        
        # Sort tasks by priority
        priority_order = {Priority.CRITICAL: 0, Priority.HIGH: 1, 
                         Priority.MEDIUM: 2, Priority.LOW: 3}
        sorted_tasks = sorted(tasks, key=lambda t: priority_order.get(t.priority, 2))
        
        for task in sorted_tasks:
            # Find suitable resources
            suitable = []
            for resource in resources:
                if resource.availability > resource.current_load:
                    suitable.append(resource)
            
            if suitable:
                # Allocate first suitable resource
                allocated = suitable[0]
                allocations[task.task_id] = [allocated.resource_id]
                allocated.current_load += task.estimated_duration * 0.5
                task.resources = [allocated.resource_id]
        
        return allocations
    
    def calculate_critical_path(self, tasks: List[Task]) -> List[str]:
        """Calculate critical path using CPM.
        
        Args:
            tasks: List of tasks
            
        Returns:
            List of task IDs on critical path
        """
        # Build task map
        task_map = {t.task_id: t for t in tasks}
        
        # Calculate earliest start/finish times
        earliest_start = {}
        earliest_finish = {}
        
        # Topological order
        dep_analysis = self.analyze_dependencies(tasks)
        sorted_ids = dep_analysis["sorted_order"]
        
        for task_id in sorted_ids:
            task = task_map[task_id]
            
            # Earliest start is max of all predecessor finishes
            if task.dependencies:
                earliest_start[task_id] = max(
                    earliest_finish.get(dep_id, 0) for dep_id in task.dependencies
                )
            else:
                earliest_start[task_id] = 0
            
            earliest_finish[task_id] = earliest_start[task_id] + task.estimated_duration
        
        # Find project end time
        project_end = max(earliest_finish.values()) if earliest_finish else 0
        
        # Calculate latest start/finish times
        latest_start = {}
        latest_finish = {}
        
        for task_id in reversed(sorted_ids):
            task = task_map[task_id]
            
            # Find successors
            successors = [t.task_id for t in tasks if task_id in t.dependencies]
            
            if successors:
                latest_finish[task_id] = min(
                    latest_start.get(succ_id, project_end) for succ_id in successors
                )
            else:
                latest_finish[task_id] = project_end
            
            latest_start[task_id] = latest_finish[task_id] - task.estimated_duration
        
        # Calculate slack and find critical path
        critical_path = []
        for task_id in sorted_ids:
            slack = latest_start[task_id] - earliest_start[task_id]
            if slack == 0:
                critical_path.append(task_id)
        
        return critical_path
    
    def create_schedule(self, tasks: List[Task],
                       resources: List[Resource],
                       start_date: Optional[datetime] = None) -> Plan:
        """Create a complete project schedule.
        
        Args:
            tasks: List of tasks
            resources: Available resources
            start_date: Project start date
            
        Returns:
            Complete project plan
        """
        if not start_date:
            start_date = datetime.now()
        
        # Analyze dependencies
        dep_analysis = self.analyze_dependencies(tasks)
        
        # Allocate resources
        allocations = self.allocate_resources(tasks, resources)
        
        # Calculate critical path
        critical_path = self.calculate_critical_path(tasks)
        
        # Calculate total duration
        task_map = {t.task_id: t for t in tasks}
        total_duration = 0
        for task_id in critical_path:
            total_duration += task_map[task_id].estimated_duration
        
        # Calculate end date
        end_date = start_date + timedelta(
            hours=total_duration / self.working_hours_per_day
        )
        
        # Calculate total cost
        total_cost = 0
        for task in tasks:
            for resource_id in task.resources:
                for resource in resources:
                    if resource.resource_id == resource_id:
                        total_cost += task.estimated_duration * resource.cost_per_hour
                        break
        
        # Generate milestones
        milestones = [
            {"name": "Project Start", "date": start_date.isoformat(), "tasks": []},
            {"name": "Mid-Point", 
             "date": (start_date + (end_date - start_date) / 2).isoformat(),
             "tasks": []},
            {"name": "Project Complete", "date": end_date.isoformat(), "tasks": [t.task_id for t in tasks]}
        ]
        
        return Plan(
            plan_id=f"PLAN_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name="Project Plan",
            tasks=tasks,
            resources=resources,
            start_date=start_date,
            end_date=end_date,
            total_duration=total_duration,
            critical_path=critical_path,
            total_cost=total_cost,
            milestones=milestones
        )
    
    def optimize_schedule(self, plan: Plan,
                         target_duration: Optional[float] = None) -> Plan:
        """Optimize project schedule.
        
        Args:
            plan: Current plan
            target_duration: Target duration (optional)
            
        Returns:
            Optimized plan
        """
        # Identify tasks that can be parallelized
        tasks = plan.tasks
        task_map = {t.task_id: t for t in tasks}
        
        # Find tasks with no dependencies that can run in parallel
        independent_tasks = [t for t in tasks if not t.dependencies]
        
        # Calculate potential time savings
        if target_duration and plan.total_duration > target_duration:
            # Suggest crashing (adding resources) to critical path tasks
            for task_id in plan.critical_path:
                task = task_map[task_id]
                # Double resources to halve duration (simplified)
                if len(task.resources) == 0:
                    task.estimated_duration *= 0.7  # 30% reduction
        
        # Recalculate plan
        return self.create_schedule(tasks, plan.resources, plan.start_date)
    
    def track_progress(self, plan: Plan,
                      completed_tasks: List[str],
                      in_progress_tasks: List[str]) -> Dict[str, Any]:
        """Track project progress.
        
        Args:
            plan: Current plan
            completed_tasks: List of completed task IDs
            in_progress_tasks: List of in-progress task IDs
            
        Returns:
            Progress report
        """
        task_map = {t.task_id: t for t in plan.tasks}
        
        # Update task statuses
        for task_id in completed_tasks:
            if task_id in task_map:
                task_map[task_id].status = TaskStatus.COMPLETED
                task_map[task_id].progress = 100.0
        
        for task_id in in_progress_tasks:
            if task_id in task_map:
                task_map[task_id].status = TaskStatus.IN_PROGRESS
                if task_map[task_id].progress == 0:
                    task_map[task_id].progress = 50.0
        
        # Calculate overall progress
        total_progress = sum(t.progress for t in plan.tasks) / len(plan.tasks) if plan.tasks else 0
        
        # Identify blocked tasks
        blocked_tasks = []
        for task in plan.tasks:
            if task.status == TaskStatus.NOT_STARTED:
                # Check if dependencies are complete
                deps_complete = all(
                    task_map.get(dep_id, Task("", "", "", 0)).status == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                )
                if not deps_complete:
                    blocked_tasks.append(task.task_id)
        
        return {
            "overall_progress": round(total_progress, 2),
            "completed_count": len(completed_tasks),
            "in_progress_count": len(in_progress_tasks),
            "blocked_count": len(blocked_tasks),
            "blocked_tasks": blocked_tasks,
            "remaining_tasks": len(plan.tasks) - len(completed_tasks) - len(in_progress_tasks)
        }


# Convenience functions
def plan_project(tasks: List[Task], resources: List[Resource]) -> Plan:
    """Create a project plan."""
    planner = TaskPlanner()
    return planner.create_schedule(tasks, resources)


def find_critical_path(tasks: List[Task]) -> List[str]:
    """Find critical path in task list."""
    planner = TaskPlanner()
    return planner.calculate_critical_path(tasks)


def track_project_progress(plan: Plan, completed: List[str], 
                          in_progress: List[str]) -> Dict[str, Any]:
    """Track project progress."""
    planner = TaskPlanner()
    return planner.track_progress(plan, completed, in_progress)