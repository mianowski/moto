from ..batch.models import batch_backends, BaseBackend, Job, ClientException
from ..core.utils import BackendDict

import datetime


class BatchSimpleBackend(BaseBackend):
    """
    Implements a Batch-Backend that does not use Docker containers. Submitted Jobs are simply marked as Success
    Use the `@mock_batch_simple`-decorator to use this class.
    """

    def __init__(self, region_name=None):
        self.region_name = region_name

    @property
    def backend(self):
        return batch_backends[self.region_name]

    def __getattribute__(self, name):
        """
        Magic part that makes this class behave like a wrapper around the regular batch_backend
        We intercept calls to `submit_job` and replace this with our own (non-Docker) implementation
        Every other method call is send through to batch_backend
        """
        if name in [
            "backend",
            "region_name",
            "urls",
            "_url_module",
            "__class__",
            "url_bases",
        ]:
            return object.__getattribute__(self, name)
        if name in ["submit_job"]:

            def newfunc(*args, **kwargs):
                attr = object.__getattribute__(self, name)
                return attr(*args, **kwargs)

            return newfunc
        else:
            return object.__getattribute__(self.backend, name)

    def submit_job(
        self,
        job_name,
        job_def_id,
        job_queue,
        depends_on=None,
        container_overrides=None,
        timeout=None,
    ):
        # Look for job definition
        job_def = self.get_job_definition(job_def_id)
        if job_def is None:
            raise ClientException(
                "Job definition {0} does not exist".format(job_def_id)
            )

        queue = self.get_job_queue(job_queue)
        if queue is None:
            raise ClientException("Job queue {0} does not exist".format(job_queue))

        job = Job(
            job_name,
            job_def,
            queue,
            log_backend=self.logs_backend,
            container_overrides=container_overrides,
            depends_on=depends_on,
            all_jobs=self._jobs,
            timeout=timeout,
        )
        self.backend._jobs[job.job_id] = job

        # We don't want to actually run the job - just mark it as succeeded
        job.job_started_at = datetime.datetime.now()
        job._start_attempt()
        job._mark_stopped(success=True)

        return job_name, job.job_id


batch_simple_backends = BackendDict(BatchSimpleBackend, "batch")
