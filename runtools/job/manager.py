import time
import numpy as np

from runtools.utils.python import cmd
from runtools.settings import LOGIN, MAX_DEFAULT_CORES, MAX_BESTEFFORT_CORES

""" Class of functions that take a list of JobMeta as input """


def manage(jobs_all, telegram_callback):
    jobs_names = [job.job_name for job in jobs_all]
    jobs_waiting = jobs_all.copy()  # type: list[JobMeta]
    jobs_running = []
    # create the job scripts
    for job in jobs_all:
        job.generate_script()

    # launch the jobs
    # while (jobs_waiting or any([not job.is_completed for job in jobs])):
    while (jobs_waiting or jobs_running):
        # select jobs to run
        selected_jobs = []
        for job in jobs_waiting:
            if job.is_ready_to_start:
                selected_jobs.append(job)
                jobs_waiting.remove(job)
        # run jobs w.r.t. their priority
        selected_jobs.sort(key=lambda x: x.priority_level, reverse=True)
        for job in selected_jobs:
            job.run()
            jobs_running.append(job)
        telegram_callback(jobs_all)

        # some sleeping between each loop
        time.sleep(1)
        # check which jobs were already completed
        for job in jobs_running.copy():
            if job.is_completed:
                jobs_running.remove(job)
        # check which jobs were stuck
        for job in jobs_running.copy():
            if job.is_stuck:
                print('Job {} was stuck, will relaunch it'.format(job.job_name))
                job.kill()
                jobs_waiting.append(job)
                jobs_running.remove(job)

    # report the last time (if needed)
    telegram_callback(jobs_all)
    print('All the jobs were finished:')
    print(jobs_names)
