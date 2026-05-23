"""Unit tests for src/jobs.py."""



from src.jobs import Job, JobQueue


class TestJob:
    def test_job_creation(self):
        """A Job is created with correct defaults."""
        job = Job(id="abc123", scraper="amazon", params={"keyword": "laptop"})
        assert job.id == "abc123"
        assert job.scraper == "amazon"
        assert job.params == {"keyword": "laptop"}
        assert job.status == "pending"
        assert job.result is None
        assert job.error is None

    def test_job_to_dict(self):
        """to_dict returns a plain dict with all fields."""
        job = Job(id="x", scraper="ebay", params={"search": "macbook"})
        d = job.to_dict()
        assert isinstance(d, dict)
        assert d["id"] == "x"
        assert d["scraper"] == "ebay"
        assert d["status"] == "pending"


class TestJobQueue:
    def test_enqueue_returns_job_metadata(self):
        """enqueue() returns a dict with id, status, created_at."""
        q = JobQueue(max_size=10)
        result = q.enqueue("amazon", {"keyword": "phone"})
        assert "id" in result
        assert result["status"] == "pending"
        assert "created_at" in result

    def test_get_returns_none_for_unknown_id(self):
        """get() returns None for a job that does not exist."""
        q = JobQueue(max_size=10)
        assert q.get("does-not-exist") is None

    def test_get_returns_job_after_enqueue(self):
        """get() returns job metadata after enqueue."""
        q = JobQueue(max_size=10)
        result = q.enqueue("supermarket", {"retailer": "tesco"})
        job = q.get(result["id"])
        assert job is not None
        assert job["id"] == result["id"]
        assert job["status"] in ("pending", "running", "done")

    def test_list_all_empty_queue(self):
        """list_all() on a fresh queue returns an empty list."""
        q = JobQueue(max_size=10)
        assert q.list_all() == []

    def test_list_all_returns_jobs(self):
        """list_all() returns enqueued jobs sorted newest-first."""
        q = JobQueue(max_size=10)
        q.enqueue("amazon", {"keyword": "a"})
        q.enqueue("ebay", {"search": "b"})
        jobs = q.list_all()
        assert len(jobs) == 2
        assert all(isinstance(j, dict) for j in jobs)

    def test_queue_size_increments(self):
        """queue_size reflects pending jobs."""
        q = JobQueue(max_size=10)
        initial = q.queue_size
        q.enqueue("amazon", {"keyword": "test"})
        assert q.queue_size == initial + 1

    def test_job_count_tracks_all_jobs(self):
        """job_count tracks total jobs ever enqueued."""
        q = JobQueue(max_size=10)
        assert q.job_count == 0
        q.enqueue("amazon", {"keyword": "one"})
        assert q.job_count == 1
        q.enqueue("ebay", {"search": "two"})
        assert q.job_count == 2

    def test_shutdown_stops_worker(self):
        """shutdown() sets _running to False."""
        q = JobQueue(max_size=10)
        q.shutdown()
        assert q._running is False
