"""Tests for Sprint 3: Experience & Lessons Learned.

Tests:
- ExperienceStore: Add, search, pattern matching
- LessonLearner: Extract lessons, recommend, verify
- BestPracticesLibrary: Add, approve, recommend practices
"""
import pytest
import json
from pathlib import Path
import tempfile
import shutil

from quan_ai_brain.memory.experience_store import (
    ExperienceStore, Experience, OutcomeType, ExperienceType
)
from quan_ai_brain.memory.lesson_learner import (
    LessonLearner, Lesson, LessonCategory
)
from quan_ai_brain.memory.best_practices import (
    BestPracticesLibrary, BestPractice, PracticeStatus, PracticeDomain
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_brain.db"
    
    yield str(db_path)
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def experience_store(temp_db):
    """Create an ExperienceStore instance."""
    return ExperienceStore(db_path=temp_db)


@pytest.fixture
def lesson_learner(experience_store):
    """Create a LessonLearner instance."""
    return LessonLearner(experience_store)


@pytest.fixture
def best_practices(temp_db, experience_store):
    """Create a BestPracticesLibrary instance."""
    return BestPracticesLibrary(db_path=temp_db, experience_store=experience_store)


class TestExperienceStore:
    """Tests for ExperienceStore class."""
    
    def test_add_experience(self, experience_store):
        """Test adding a new experience."""
        exp = experience_store.add_experience(
            experience_type=ExperienceType.TASK,
            title="Test Task",
            description="Testing a task",
            context={"user": "test", "priority": "high"},
            action_taken="Completed the task",
            outcome=OutcomeType.SUCCESS,
            outcome_details="Task completed successfully",
            lessons_learned="Always test thoroughly",
            tags=["test", "task"],
            metadata={"version": "1.0"}
        )
        
        assert exp.id is not None
        assert exp.experience_type == ExperienceType.TASK
        assert exp.outcome == OutcomeType.SUCCESS
        assert "test" in json.loads(exp.tags_json)
    
    def test_get_experience(self, experience_store):
        """Test getting experience by ID."""
        exp = experience_store.add_experience(
            experience_type=ExperienceType.WORKFLOW,
            title="Test Workflow",
            description="Testing workflow",
            context={},
            action_taken="Executed workflow",
            outcome=OutcomeType.SUCCESS
        )
        
        retrieved = experience_store.get_experience(exp.id)
        
        assert retrieved is not None
        assert retrieved.title == "Test Workflow"
        assert retrieved.experience_type == ExperienceType.WORKFLOW
    
    def test_search_experiences_by_outcome(self, experience_store):
        """Test searching experiences by outcome."""
        experience_store.add_experience(
            experience_type=ExperienceType.TASK,
            title="Success Task",
            description="Success",
            context={},
            action_taken="Done",
            outcome=OutcomeType.SUCCESS
        )
        
        experience_store.add_experience(
            experience_type=ExperienceType.TASK,
            title="Failure Task",
            description="Failure",
            context={},
            action_taken="Failed",
            outcome=OutcomeType.FAILURE
        )
        
        successes = experience_store.search_experiences(outcome=OutcomeType.SUCCESS)
        failures = experience_store.search_experiences(outcome=OutcomeType.FAILURE)
        
        assert len(successes) == 1
        assert len(failures) == 1
    
    def test_search_experiences_by_tags(self, experience_store):
        """Test searching experiences by tags."""
        experience_store.add_experience(
            experience_type=ExperienceType.TASK,
            title="Task 1",
            description="Test",
            context={},
            action_taken="Done",
            outcome=OutcomeType.SUCCESS,
            tags=["python", "testing"]
        )
        
        experience_store.add_experience(
            experience_type=ExperienceType.TASK,
            title="Task 2",
            description="Test",
            context={},
            action_taken="Done",
            outcome=OutcomeType.SUCCESS,
            tags=["javascript", "testing"]
        )
        
        results = experience_store.search_experiences(tags=["python"])
        
        assert len(results) == 1
        assert results[0].title == "Task 1"
    
    def test_find_similar_experiences(self, experience_store):
        """Test finding similar experiences."""
        experience_store.add_experience(
            experience_type=ExperienceType.PROBLEM_SOLVING,
            title="Database Issue",
            description="Fixed database connection",
            context={"db_type": "postgresql", "error": "connection_timeout"},
            action_taken="Increased timeout",
            outcome=OutcomeType.SUCCESS
        )
        
        experience_store.add_experience(
            experience_type=ExperienceType.PROBLEM_SOLVING,
            title="API Issue",
            description="Fixed API timeout",
            context={"api_type": "rest", "error": "timeout"},
            action_taken="Increased timeout",
            outcome=OutcomeType.SUCCESS
        )
        
        # Search for similar database issue
        matches = experience_store.find_similar_experiences(
            context={"db_type": "postgresql", "error": "connection_timeout"},
            experience_type=ExperienceType.PROBLEM_SOLVING
        )
        
        assert len(matches) > 0
        assert matches[0].similarity_score > 0.3
    
    def test_get_outcome_statistics(self, experience_store):
        """Test getting outcome statistics."""
        experience_store.add_experience(
            experience_type=ExperienceType.TASK,
            title="Success 1",
            description="Test",
            context={},
            action_taken="Done",
            outcome=OutcomeType.SUCCESS
        )
        
        experience_store.add_experience(
            experience_type=ExperienceType.TASK,
            title="Success 2",
            description="Test",
            context={},
            action_taken="Done",
            outcome=OutcomeType.SUCCESS
        )
        
        experience_store.add_experience(
            experience_type=ExperienceType.TASK,
            title="Failure",
            description="Test",
            context={},
            action_taken="Failed",
            outcome=OutcomeType.FAILURE
        )
        
        stats = experience_store.get_outcome_statistics()
        
        assert stats['total_experiences'] == 3
        assert stats['success_count'] == 2
        assert stats['failure_count'] == 1
        assert stats['success_rate'] > 60
    
    def test_get_lessons_learned(self, experience_store):
        """Test getting lessons learned."""
        experience_store.add_experience(
            experience_type=ExperienceType.TASK,
            title="Task with lesson",
            description="Test",
            context={},
            action_taken="Done",
            outcome=OutcomeType.SUCCESS,
            lessons_learned="Important lesson here"
        )
        
        lessons = experience_store.get_lessons_learned()
        
        assert len(lessons) > 0
        assert "Important lesson here" in lessons[0]['lesson']
    
    def test_update_experience(self, experience_store):
        """Test updating experience."""
        exp = experience_store.add_experience(
            experience_type=ExperienceType.TASK,
            title="Test",
            description="Test",
            context={},
            action_taken="Done",
            outcome=OutcomeType.SUCCESS
        )
        
        experience_store.update_experience(
            exp.id,
            lessons_learned="New lesson",
            metadata={"updated": True}
        )
        
        updated = experience_store.get_experience(exp.id)
        
        assert updated.lessons_learned == "New lesson"
        assert json.loads(updated.metadata_json)['updated'] is True


class TestLessonLearner:
    """Tests for LessonLearner class."""
    
    def test_extract_success_lessons(self, lesson_learner):
        """Test extracting lessons from success."""
        exp = lesson_learner.experience_store.add_experience(
            experience_type=ExperienceType.TASK,
            title="Successful Task",
            description="Completed successfully",
            context={"complexity": "high"},
            action_taken="Used best practices",
            outcome=OutcomeType.SUCCESS,
            outcome_details="All tests passed"
        )
        
        lessons = lesson_learner.extract_lessons_from_experience(exp.id)
        
        assert len(lessons) > 0
        assert any(l.category == LessonCategory.BEST_PRACTICE for l in lessons)
    
    def test_extract_failure_lessons(self, lesson_learner):
        """Test extracting lessons from failure."""
        exp = lesson_learner.experience_store.add_experience(
            experience_type=ExperienceType.TASK,
            title="Failed Task",
            description="Failed",
            context={},
            action_taken="Wrong approach",
            outcome=OutcomeType.FAILURE,
            outcome_details="Timeout error"
        )
        
        lessons = lesson_learner.extract_lessons_from_experience(exp.id)
        
        assert len(lessons) > 0
        assert any(l.category == LessonCategory.PITFALL for l in lessons)
        assert any(l.category == LessonCategory.WARNING for l in lessons)
    
    def test_extract_partial_lessons(self, lesson_learner):
        """Test extracting lessons from partial success."""
        exp = lesson_learner.experience_store.add_experience(
            experience_type=ExperienceType.TASK,
            title="Partial Task",
            description="Partial",
            context={},
            action_taken="Partial work",
            outcome=OutcomeType.PARTIAL,
            outcome_details="Some parts failed"
        )
        
        lessons = lesson_learner.extract_lessons_from_experience(exp.id)
        
        assert len(lessons) > 0
        assert any(l.category == LessonCategory.TIP for l in lessons)
    
    def test_search_lessons(self, lesson_learner):
        """Test searching lessons."""
        # Create experience and extract lessons
        exp = lesson_learner.experience_store.add_experience(
            experience_type=ExperienceType.TASK,
            title="Test",
            description="Test",
            context={},
            action_taken="Done",
            outcome=OutcomeType.SUCCESS
        )
        
        lesson_learner.extract_lessons_from_experience(exp.id)
        
        # Search by category
        best_practices = lesson_learner.search_lessons(
            category=LessonCategory.BEST_PRACTICE
        )
        
        assert len(best_practices) > 0
    
    def test_recommend_lessons(self, lesson_learner):
        """Test recommending lessons."""
        # Add experience
        exp = lesson_learner.experience_store.add_experience(
            experience_type=ExperienceType.PROBLEM_SOLVING,
            title="Database Fix",
            description="Fixed database issue",
            context={"db_type": "postgresql", "error": "timeout"},
            action_taken="Increased timeout",
            outcome=OutcomeType.SUCCESS
        )
        
        lesson_learner.extract_lessons_from_experience(exp.id)
        
        # Recommend for similar context
        recommendations = lesson_learner.recommend_lessons(
            context={"db_type": "postgresql", "error": "timeout"},
            experience_type=ExperienceType.PROBLEM_SOLVING
        )
        
        assert len(recommendations) > 0
    
    def test_verify_lesson(self, lesson_learner):
        """Test verifying a lesson."""
        exp = lesson_learner.experience_store.add_experience(
            experience_type=ExperienceType.TASK,
            title="Test",
            description="Test",
            context={},
            action_taken="Done",
            outcome=OutcomeType.SUCCESS
        )
        
        lessons = lesson_learner.extract_lessons_from_experience(exp.id)
        
        if lessons:
            lesson_learner.verify_lesson(
                lessons[0].id,
                verified=True,
                verification_note="Verified by expert"
            )
            
            verified = lesson_learner.get_lesson(lessons[0].id)
            assert verified.verified is True
    
    def test_get_lesson_statistics(self, lesson_learner):
        """Test getting lesson statistics."""
        exp = lesson_learner.experience_store.add_experience(
            experience_type=ExperienceType.TASK,
            title="Test",
            description="Test",
            context={},
            action_taken="Done",
            outcome=OutcomeType.SUCCESS
        )
        
        lesson_learner.extract_lessons_from_experience(exp.id)
        
        stats = lesson_learner.get_lesson_statistics()
        
        assert stats['total_lessons'] > 0
        assert 'by_category' in stats


class TestBestPracticesLibrary:
    """Tests for BestPracticesLibrary class."""
    
    def test_add_practice(self, best_practices):
        """Test adding a best practice."""
        practice = best_practices.add_practice(
            title="Test Best Practice",
            description="A test practice",
            domain=PracticeDomain.DEVELOPMENT,
            category="Testing",
            steps=["Step 1", "Step 2", "Step 3"],
            benefits="Improved quality",
            when_to_use="Before deployment",
            when_avoid="Not for prototypes",
            tags=["testing", "quality"]
        )
        
        assert practice.id is not None
        assert practice.status == PracticeStatus.DRAFT
        assert practice.domain == PracticeDomain.DEVELOPMENT
    
    def test_approve_practice(self, best_practices):
        """Test approving a best practice."""
        practice = best_practices.add_practice(
            title="Test Practice",
            description="Test",
            domain=PracticeDomain.OPERATIONS,
            category="Deployment",
            steps=["Step 1"],
            benefits="Faster deployment",
            when_to_use="Always"
        )
        
        best_practices.approve_practice(practice.id, "reviewer1")
        
        approved = best_practices.get_practice(practice.id)
        
        assert approved.status == PracticeStatus.APPROVED
        assert approved.reviewed_by == "reviewer1"
    
    def test_search_practices(self, best_practices):
        """Test searching practices."""
        best_practices.add_practice(
            title="Dev Practice",
            description="Test",
            domain=PracticeDomain.DEVELOPMENT,
            category="Coding",
            steps=["Step 1"],
            benefits="Better code",
            when_to_use="Always"
        )
        
        best_practices.add_practice(
            title="Ops Practice",
            description="Test",
            domain=PracticeDomain.OPERATIONS,
            category="Deployment",
            steps=["Step 1"],
            benefits="Faster deploy",
            when_to_use="Always"
        )
        
        dev_practices = best_practices.search_practices(
            domain=PracticeDomain.DEVELOPMENT
        )
        
        assert len(dev_practices) == 1
    
    def test_log_usage(self, best_practices):
        """Test logging practice usage."""
        practice = best_practices.add_practice(
            title="Test",
            description="Test",
            domain=PracticeDomain.GENERAL,
            category="General",
            steps=["Step 1"],
            benefits="Benefit",
            when_to_use="Always"
        )
        
        best_practices.log_usage(
            practice.id,
            context={"scenario": "test"},
            outcome="success",
            effectiveness_score=0.9,
            notes="Worked well"
        )
        
        effectiveness = best_practices.get_practice_effectiveness(practice.id)
        
        assert effectiveness['total_usage'] == 1
        assert effectiveness['avg_effectiveness'] == 0.9
    
    def test_recommend_practices(self, best_practices):
        """Test recommending practices."""
        best_practices.add_practice(
            title="Approved Practice",
            description="Test",
            domain=PracticeDomain.SECURITY,
            category="Authentication",
            steps=["Step 1"],
            benefits="Better security",
            when_to_use="Always"
        )
        
        # Approve it
        practices = best_practices.search_practices(domain=PracticeDomain.SECURITY)
        if practices:
            best_practices.approve_practice(practices[0].id, "reviewer")
        
        recommendations = best_practices.recommend_practices(
            domain=PracticeDomain.SECURITY
        )
        
        assert len(recommendations) > 0
        assert all(p.status == PracticeStatus.APPROVED for p in recommendations)
    
    def test_get_statistics(self, best_practices):
        """Test getting library statistics."""
        best_practices.add_practice(
            title="Practice 1",
            description="Test",
            domain=PracticeDomain.DEVELOPMENT,
            category="Coding",
            steps=["Step 1"],
            benefits="Benefit",
            when_to_use="Always"
        )
        
        stats = best_practices.get_statistics()
        
        assert stats['total_practices'] >= 1
        assert 'by_domain' in stats
        assert 'by_status' in stats
    
    def test_create_from_experience(self, best_practices):
        """Test creating practice from experience."""
        exp = best_practices.experience_store.add_experience(
            experience_type=ExperienceType.TASK,
            title="Successful Task",
            description="Completed successfully",
            context={},
            action_taken="Used proper testing",
            outcome=OutcomeType.SUCCESS,
            outcome_details="All tests passed"
        )
        
        practice = best_practices.create_from_experience(exp.id)
        
        assert practice is not None
        assert practice.status == PracticeStatus.DRAFT
        assert "Successful Task" in practice.title


class TestExperienceIntegration:
    """Integration tests for experience system."""
    
    def test_full_experience_to_practice_workflow(self, temp_db):
        """Test complete workflow from experience to best practice."""
        store = ExperienceStore(db_path=temp_db)
        learner = LessonLearner(store)
        library = BestPracticesLibrary(db_path=temp_db, experience_store=store)
        
        # Add successful experience
        exp = store.add_experience(
            experience_type=ExperienceType.PROBLEM_SOLVING,
            title="Database Optimization",
            description="Optimized database queries",
            context={"db_type": "postgresql", "query_type": "complex"},
            action_taken="Added indexes and optimized queries",
            outcome=OutcomeType.SUCCESS,
            outcome_details="Query time reduced by 80%",
            lessons_learned="Always profile before optimizing",
            tags=["database", "performance"]
        )
        
        # Extract lessons
        lessons = learner.extract_lessons_from_experience(exp.id)
        assert len(lessons) > 0
        
        # Create best practice
        practice = library.create_from_experience(exp.id)
        assert practice is not None
        
        # Approve practice
        library.approve_practice(practice.id, "expert")
        
        # Verify in recommendations - use GENERAL domain since practice was created with GENERAL
        recommendations = library.recommend_practices(
            domain=PracticeDomain.GENERAL
        )
        
        assert any(p.id == practice.id for p in recommendations)
    
    def test_lesson_recommendation_accuracy(self, temp_db):
        """Test lesson recommendation accuracy."""
        store = ExperienceStore(db_path=temp_db)
        learner = LessonLearner(store)
        
        # Add multiple experiences
        store.add_experience(
            experience_type=ExperienceType.PROBLEM_SOLVING,
            title="API Timeout",
            description="Fixed API timeout",
            context={"api_type": "rest", "error": "timeout"},
            action_taken="Increased timeout and added retry",
            outcome=OutcomeType.SUCCESS
        )
        
        store.add_experience(
            experience_type=ExperienceType.PROBLEM_SOLVING,
            title="Database Timeout",
            description="Fixed database timeout",
            context={"db_type": "postgresql", "error": "timeout"},
            action_taken="Added connection pooling",
            outcome=OutcomeType.SUCCESS
        )
        
        # Extract lessons
        for exp in store.search_experiences(limit=10):
            learner.extract_lessons_from_experience(exp.id)
        
        # Recommend for API timeout
        api_recommendations = learner.recommend_lessons(
            context={"api_type": "rest", "error": "timeout"},
            experience_type=ExperienceType.PROBLEM_SOLVING
        )
        
        # Should recommend API-related lessons
        assert len(api_recommendations) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])