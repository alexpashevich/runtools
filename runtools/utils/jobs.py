import os
import telegram_send

from runtools.utils import config, system
from runtools.job.manager import manage

STATUS_WAITING = 1
STATUS_LAUNCHED = 2
STATUS_CRASHED = 3
STATUS_DONE = 4


def run_locally(exp_name, args, script, args_file, seed, render, debug):
    # log dir creation
    if 'collect' in script and seed is not None:
        args = config.append_args(args, ['{}={}'.format('collect.env.seed', seed)])
    # set up the paths (replace the paths from USED_CODE_DIRS with the ones in a cached code dir)
    python_path = system.get_python_path(exp_name)
    args = config.append_log_dir(args, exp_name, args_file, script)
    script = 'PYTHONPATH={} python3 -u -m {} {}'.format(python_path, script, args)
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
    jobs_status = [0] * len(jobs)
    def telegram_callback(jobs_all, jobs_waiting, counter, print_every=20):
        # report that the manager is still waiting for some jobs
        if counter % print_every == 0:
            jobs_ids_to_finish = [[j.job_id for j in job.previous_jobs] for job in jobs_waiting]
            print('{} job(s) is(are) waiting {} jobs to finish'.format(
                len(jobs_waiting), set(sum(jobs_ids_to_finish, []))))
        # send messages to telegram
        for idx, job in enumerate(jobs_all):
            report_message = ''
            if job.job_id is None and job.previous_jobs and jobs_status[idx] < STATUS_WAITING:
                report_message = 'job `{0}` is waiting\n```details = {1}```'.format(
                    exp_names[idx], exp_metas[idx])
                jobs_status[idx] = STATUS_WAITING
            elif job.job_id is not None and jobs_status[idx] < STATUS_LAUNCHED:
                report_message = 'launched job `{0}`\n```details = {1}```'.format(
                    exp_names[idx], exp_metas[idx])
                jobs_status[idx] = STATUS_LAUNCHED
            elif job.job_crashed and jobs_status[idx] < STATUS_CRASHED:
                report_message = 'job `{0}` has crashed'.format(
                    exp_names[idx], exp_metas[idx])
                jobs_status[idx] = STATUS_CRASHED
            elif job.job_ended and jobs_status[idx] < STATUS_DONE:
                report_message = 'job `{0}` has finished successfully'.format(
                    exp_names[idx], exp_metas[idx])
                jobs_status[idx] = STATUS_DONE
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
    # running the jobs
    manage(jobs, telegram_callback)
    print('All the jobs were executed')
