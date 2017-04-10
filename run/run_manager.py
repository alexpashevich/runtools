from run.run_meta import RunMeta
from pytools.tools import cmd
from settings import LOGIN, MAX_DEFAULT_JOBS

""" Class of functions that take a list of RunMeta as input """


def manage(runs, sleep_duration=1):
    runs_waiting_previous_jobs = runs  # type: list[RunMeta]
    runs_waiting_max_default_jobs = []  # type: list[RunMeta]
    while runs_waiting_previous_jobs != [] or runs_waiting_max_default_jobs != []:
        # runs waiting because of previous jobs
        selected_runs = []
        for run in runs_waiting_previous_jobs:
            if run.previous_jobs_ended:
                selected_runs.append(run)
        for run in selected_runs:
            runs_waiting_previous_jobs.remove(run)
            runs_waiting_max_default_jobs.append(run)
        # runs waiting are sorted by the inverse order of priority
        runs_waiting_max_default_jobs.sort(key=lambda x: x.priority_level, reverse=True)
        # runs waiting because of max default jobs
        selected_runs = []
        for run in runs_waiting_max_default_jobs:
            if run_available(run.machine_name, selected_runs):
                selected_runs.append(run)
        for run in selected_runs:
            run.run()
            runs_waiting_max_default_jobs.remove(run)
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
