import time
import numpy as np

from runtools.utils.python import cmd
from runtools.settings import LOGIN, MAX_TIMES_RESTART_CRASHED_JOB, JobStatus

""" Class of functions that take a list of JobMeta as input """


def manage(jobs_list, telegram_callback):
    # jobs_list.sort(key=lambda x: x.name)
    # create the job scripts
    for job in jobs_list:
        job.generate_script()
    all_jobs_are_done = False

    # keep scheduling the jobs until all have status DONE_SUCCESS or DONE_FAILURE
    while not all_jobs_are_done:
        # check status of jobs and maybe (re)launch some of them
        for job in jobs_list:
            job_status = job.status()
            if job_status == JobStatus.READY_TO_START:
                # schedule the job and set status to SCHEDULED
                job.run()
            elif job_status == JobStatus.STUCK:
                # kill and set status to READY_TO_START
                job.kill_stuck()
            elif job_status == JobStatus.CRASHED:
                # maybe set status to READY_TO_START
                job.restart_crashed()
            if job_status in (JobStatus.WAITING_PREVIOUS,
                              JobStatus.SCHEDULED,
                              JobStatus.RUNNING,
                              JobStatus.DONE_FAILURE,
                              JobStatus.DONE_SUCCESS):
                # do nothing
                pass

        # some sleeping between each loop
        time.sleep(1)
        all_jobs_are_done = all([j._status in (JobStatus.DONE_SUCCESS, JobStatus.DONE_FAILURE) for j in jobs_list])
        telegram_callback(jobs_list)

    print('All the jobs were completed')
    for job in jobs_list:
        print('Job {} with status {}'.format(job.name, job._status))
