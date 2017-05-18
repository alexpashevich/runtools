from job.job_meta import JobMeta
from pytools.tools import cmd
from settings import LOGIN, MAX_DEFAULT_JOBS

""" Class of functions that take a list of JobMeta as input """


def manage(jobs, only_initialization=True, sleep_duration=20):
    jobs_waiting_previous_jobs = jobs  # type: list[JobMeta]
    jobs_waiting_max_default_jobs = []  # type: list[JobMeta]
    # initialize jobs
    print('Start Initialization')
    for job in jobs_waiting_previous_jobs:
        job.initialization()
    print('End Initialization')
    if not only_initialization:
        while jobs_waiting_previous_jobs != [] or jobs_waiting_max_default_jobs != []:
            # runs waiting because of previous jobs
            selected_jobs = []
            for job in jobs_waiting_previous_jobs:
                if job.previous_jobs_ended:
                    selected_jobs.append(job)
            for job in selected_jobs:
                jobs_waiting_previous_jobs.remove(job)
                jobs_waiting_max_default_jobs.append(job)
            # runs waiting are sorted by the inverse order of priority
            jobs_waiting_max_default_jobs.sort(key=lambda x: x.priority_level, reverse=True)
            # runs waiting because of max default jobs
            selected_jobs = []
            for job in jobs_waiting_max_default_jobs:
                if run_available(job.machine_name, selected_jobs):
                    selected_jobs.append(job)
            for job in selected_jobs:
                job.run()
                jobs_waiting_max_default_jobs.remove(job)
            # some sleeping between each loop
            cmd('sleep %i' % sleep_duration)


def run_available(machine_name, selected_runs):
    oarstat_lines = cmd("ssh " + machine_name + " ' oarstat ' ")
    jobs_nb = 0
    # check number of jobs on clusters
    for line in oarstat_lines:
        if LOGIN in line:
            jobs_nb += 1
    # check number of jobs already selected
    for run in selected_runs:
        if run.machine_name == machine_name:
            jobs_nb += 1
    return jobs_nb < MAX_DEFAULT_JOBS[machine_name]
