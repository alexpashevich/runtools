from runtools.utils.python import cmd
from runtools.settings import LOGIN, MAX_DEFAULT_CORES, MAX_BESTEFFORT_CORES

""" Class of functions that take a list of JobMeta as input """


def manage(jobs, callback):
    jobs_waiting_previous_jobs = jobs.copy()  # type: list[JobMeta]
    jobs_waiting_max_default_jobs = []  # type: list[JobMeta]
    # create the job script
    for job in jobs_waiting_previous_jobs:
        job.generate_script()
    # launch the jobs
    while_counter = 0
    # TODO: probably write an except/try here (e.g. if OAR does not respond)
    while (jobs_waiting_previous_jobs or jobs_waiting_max_default_jobs or any([not job.job_ended for job in jobs])):
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
            selected_jobs.append(job)
            # TODO: uncomment if you care about the limits in settings
            # if allowed(selected_jobs, job.machine_name, job.besteffort):
            #     selected_jobs.append(job)
        for job in selected_jobs:
            job.run()
            jobs_waiting_max_default_jobs.remove(job)
        # some sleeping between each loop
        callback(jobs, jobs_waiting_previous_jobs + jobs_waiting_max_default_jobs, while_counter)
        while_counter += 1
        cmd('sleep 1')
    # report the last time (if needed)
    callback(jobs, jobs_waiting_previous_jobs + jobs_waiting_max_default_jobs, while_counter)


def allowed(selected_runs, machine_name, besteffort):
    oarstat_lines = cmd("ssh " + machine_name + " ' oarstat ' ")
    cores_besteffort_nb = 0
    cores_default_nb = 0
    # check number of jobs on clusters
    for line in oarstat_lines:
        if LOGIN in line:
            try:
                job_cores = int(line.split('R=')[1].split(',')[0])
                if 'T=besteffort' not in line:
                    cores_default_nb += job_cores
                else:
                    cores_besteffort_nb += job_cores
            except:
                cores_default_nb += 8
                cores_besteffort_nb += 8

    # check number of jobs already selected
    for run in selected_runs:
        if run.machine_name == machine_name:
            if 'core=' in run.oarsub_l_options:
                job_cores = int(run.oarsub_l_options.split('core=')[1].split(',')[0])
            else:
                job_cores = 1
            if run.besteffort:
                cores_besteffort_nb += job_cores
            else:
                cores_default_nb += job_cores
    if besteffort:
        return cores_besteffort_nb < MAX_BESTEFFORT_CORES[machine_name]
    else:
        return cores_default_nb < MAX_DEFAULT_CORES[machine_name]

