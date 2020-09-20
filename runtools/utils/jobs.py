import os
import telegram_send

from runtools.utils import config, system
from runtools.job.manager import manage
from runtools.settings import JobStatus


def run_locally(exp_name, args, script, args_file, seed, render, debug, cuda_devices, run_async=False):
    # log dir creation
    if 'collect' in script and seed is not None:
        args = config.append_args(args, ['{}={}'.format('collect.env.seed', seed)])
    # set up the paths (replace the paths from USED_CODE_DIRS with the ones in a cached code dir)
    python_path = system.get_python_path(exp_name)
    args = config.append_log_dir(args, exp_name, args_file, script)
    script = 'PYTHONPATH={} python3 -u -m {} {}'.format(python_path, script, args)
    if cuda_devices is not None:
        script = 'CUDA_VISIBLE_DEVICES={} {}'.format(cuda_devices, script)
        if 'alfred.eval' in script and cuda_devices.isdigit():
            script += ' eval.x_display={}'.format(cuda_devices)
    # if render and 'collect' in script:
    #     script += ' collect.env.render=True'
    if debug:
        if 'rlons.scripts.collect' in script:
            script += ' collect.workers=0'
        elif 'rlons.scripts.train' in script:
            script += ' train.workers=0'
        elif 'alfred.train' in script or 'alfred.eval' in script:
            script += ' exp.num_workers=0'
        elif 'alfred.gen' in script:
            script += ' args.num_threads=0'
        else:
            script += ' train.workers=0 collect.workers=0'
    print('Running:\n' + script)
    if not render and 'DISPLAY' in os.environ and 'egl' in args:
        del os.environ['DISPLAY']
    os.system(script)


def init_on_cluster(exp_name, args, script, args_file, job_class):
    # log dir creation
    args = config.append_log_dir(args, exp_name, args_file, script)
    return job_class([exp_name, script, args])


def run_on_cluster(config, jobs, exp_names, exp_metas):
    reports = [-1] * len(jobs)
    def telegram_callback(jobs_list):
        # send messages to telegram
        for job_idx, job in enumerate(jobs_list):
            report_message = ''
            job_info = job.info()
            progress_str = 'N/A' if job_info is None else '{}/{}'.format(job_info['progress'], job_info['total'])
            if job._status == JobStatus.WAITING_PREVIOUS and reports[job_idx] != JobStatus.WAITING_PREVIOUS:
                report_message = 'job `{}` is waiting for previous jobs\n```details = {}```'.format(
                    exp_names[job_idx], exp_metas[job_idx])
                reports[job_idx] = JobStatus.WAITING_PREVIOUS
            elif job._status in (JobStatus.SCHEDULED, JobStatus.RUNNING) and reports[job_idx] != JobStatus.RUNNING:
                report_message = 'job `{}` was scheduled\n```details = {}```'.format(
                    exp_names[job_idx], exp_metas[job_idx])
                reports[job_idx] = JobStatus.RUNNING
            elif job._status == JobStatus.STUCK and reports[job_idx] != JobStatus.STUCK:
                report_message = 'job `{}` got stuck after {}'.format(exp_names[job_idx], progress_str)
                reports[job_idx] = JobStatus.STUCK
            elif job._status == JobStatus.CRASHED and reports[job_idx] != JobStatus.CRASHED:
                report_message = 'job `{}` has crashed after {}'.format(exp_names[job_idx], progress_str)
                reports[job_idx] = JobStatus.CRASHED
            elif job._status == JobStatus.DONE_SUCCESS and reports[job_idx] != JobStatus.DONE_SUCCESS:
                report_message = 'job `{}` has finished successfully: {}'.format(exp_names[job_idx], progress_str)
                reports[job_idx] = JobStatus.DONE_SUCCESS
            elif job._status == JobStatus.DONE_FAILURE and reports[job_idx] != JobStatus.DONE_FAILURE:
                report_message = 'job `{}` has finished with a failure: {}'.format(exp_names[job_idx], progress_str)
                reports[job_idx] = JobStatus.DONE_FAILURE
            if len(report_message) > 0:
                try:
                    telegram_send.send(messages=[report_message])
                except:
                    # TODO: why? not running this code locally anymore
                    pass

    if len(jobs) == 0:
        return
    if config.consecutive_jobs:
        # make consecutive jobs to wait for one another
        for i, job in enumerate(reversed(jobs)):
            for job_prev in jobs[:-i - 1]:
                job.add_previous_job(job_prev)
    if config.eval_type is not None and '-full' in config.eval_type:
        # make eval.select_best jobs to be scheduled after fast evaluations
        num_eval_epochs = len(range(*config.eval_full_range))
        assert len(jobs) % (num_eval_epochs + 1) == 0
        for eval_idx in range(0, len(jobs), num_eval_epochs + 1):
            eval_jobs_batch = jobs[eval_idx: eval_idx + num_eval_epochs + 1]
            for job in eval_jobs_batch[1:]:
                eval_jobs_batch[0].add_previous_job(job)

    # run the jobs with a manager loop
    manage(jobs, telegram_callback)
