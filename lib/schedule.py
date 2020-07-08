# Python job scheduling for humans.
#
# An in-process scheduler for periodic jobs that uses the builder pattern
# for configuration. Schedule lets you run Python functions (or any other
# callable) periodically at pre-determined intervals using a simple,
# human-friendly syntax.
#
# Inspired by Addam Wiggins' article "Rethinking Cron" [1] and the
# "clockwork" Ruby module [2][3].
#
# Features:
#     - A simple to use API for scheduling jobs.
#     - Very lightweight and no external dependencies.
#     - Excellent test coverage.
#     - Works with Python 2.7 and 3.3
#
# Usage:
#     >>> import schedule
#     >>> import time
#
#     >>> def job(message='stuff'):
#     >>>     print("I'm working on:", message)
#
#     >>> schedule.every(10).seconds.do(job)
#
#     >>> while True:
#     >>>     schedule.run_pending()
#     >>>     time.sleep(1)
#
# [1] http://adam.heroku.com/past/2010/4/13/rethinking_cron/
# [2] https://github.com/tomykaira/clockwork
# [3] http://adam.heroku.com/past/2010/6/30/replace_cron_with_clockwork/
import logging
import time

logger = logging.getLogger("schedule")


def now():
    return time.time()


CancelJob = object()


class Scheduler(object):
    def __init__(self):
        self.jobs = []

    def run_pending(self):
        # Run all jobs that are scheduled to run.
        #
        # Please note that it is *intended behavior that tick() does not
        # run missed jobs*. For example, if you've registered a job that
        # should run every minute and you only call tick() in one hour
        # increments then your job won't be run 60 times in between but
        # only once.
        runnable_jobs = (job for job in self.jobs if job.should_run)
        for job in sorted(runnable_jobs):
            self._run_job(job)

    def run_all(self):
        # Run all jobs regardless if they are scheduled to run or not.
        logger.info("Running *all* %i jobs", len(self.jobs))
        for job in self.jobs:
            self._run_job(job)

    def clear(self):
        # Deletes all scheduled jobs.
        del self.jobs[:]

    def cancel_job(self, job):
        # Delete a scheduled job.
        try:
            self.jobs.remove(job)
        except ValueError:
            pass

    def every(self, interval=1):
        # Schedule a new periodic job.
        job = Job(interval)
        self.jobs.append(job)
        return job

    def _run_job(self, job):
        ret = job.run()
        if ret is CancelJob:
            self.cancel_job(job)

    @property
    def next_run(self):
        # Datetime when the next job should run.
        if not self.jobs:
            return None
        return min(self.jobs).next_run

    @property
    def idle_seconds(self):
        # Number of seconds until `next_run`.
        return self.next_run - now()


class Job(object):
    # A periodic job as used by `Scheduler`.

    def __init__(self, interval):
        self.interval = interval  # pause interval
        self.job_func = None  # the job job_func to run
        self.last_run = None  # time of the last run
        self.next_run = None  # time of the next run

    def __lt__(self, other):
        # PeriodicJobs are sortable based on the scheduled time
        # they run next.
        return self.next_run < other.next_run

    @property
    def seconds(self):
        return self

    def do(self, job_func):
        # Specifies the job_func that should be called every time the
        # job runs.
        self.job_func = job_func
        self._schedule_next_run()
        return self

    @property
    def should_run(self):
        # True if the job should be run now.
        return now() >= self.next_run

    def run(self):
        # Run the job and immediately reschedule it.
        logger.debug("Running job %s", self)
        ret = self.job_func()
        self.last_run = now()
        self._schedule_next_run()
        return ret

    def _schedule_next_run(self):
        # Compute the instant when this job should run next.
        self.next_run = now() + self.interval
