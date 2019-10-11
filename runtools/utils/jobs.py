import os
import telegram_send

from runtools.utils import config
from job.manager import manage


def run_locally(exp_name, args, script, args_file, seed=None, render=False):
    # log dir creation
    if seed is None:
        seed = 0
    elif script != 'rlons.scripts.train':
        # in bc training the seed arg is not used
        argname = 'collect.seed' if script != 'ppo.train.run' else 'general.seed'
        args = config.append_args(args, ['{}={}'.format(argname, seed)])
    args = config.append_log_dir(args, exp_name, seed, args_file, script)
    script = 'python3 -u -m {} {}'.format(script, args)
    if render:
        rendering_on = ' collect.render=True'
        script += rendering_on
    print('Running:\n' + script)
    if not render and 'DISPLAY' in os.environ:
        del os.environ['DISPLAY']
    os.system(script)


def init_on_cluster(exp_name, args, script, args_file, seed, nb_seeds, job_class):
    # log dir creation
    args = config.append_log_dir(args, exp_name, seed, args_file, script)
    # adding the seed to arguments and exp_name
    if '.seed=' not in args:
        if script != 'rlons.scripts.train':
            # in bc training the seed arg is not used
            argname = 'collect.seed' if script != 'ppo.train.run' else 'general.seed'
            args = config.append_args(args, ['{}={}'.format(argname, seed)])
    else:
        if 'seed=' in args and nb_seeds > 1:
            raise ValueError(('gridsearch over seeds is launched while a seed is already' +
                              'specified in the argument file'))
    return job_class([exp_name, script, args])

def run_on_cluster(config, jobs, exp_names, exp_metas):
    jobs_reported_events = [0] * len(jobs)
    def telegram_callback(jobs_all, jobs_waiting, counter, print_every=20):
        # report that the manager is still waiting for some jobs
        if counter % print_every == 0:
            jobs_ids_to_finish = [[j.job_id for j in job.previous_jobs] for job in jobs_waiting]
            print('{} job(s) is(are) waiting {} jobs to finish'.format(
                len(jobs_waiting), set(sum(jobs_ids_to_finish, []))))
        # send messages to telegram
        for idx, job in enumerate(jobs_all):
            report_message = ''
            if job.job_id is not None and jobs_reported_events[idx] < 1:
                report_message = 'launched job `{0}`\n```details = {1}```'.format(
                    exp_names[idx], exp_metas[idx])
                jobs_reported_events[idx] = 1
            elif job.job_crashed and jobs_reported_events[idx] < 2:
                report_message = 'job `{0}` has crashed'.format(
                    exp_names[idx], exp_metas[idx])
                jobs_reported_events[idx] = 2
            elif job.job_ended and jobs_reported_events[idx] < 3:
                report_message = 'job `{0}` has finished successfully'.format(
                    exp_names[idx], exp_metas[idx])
                jobs_reported_events[idx] = 3
            if len(report_message) > 0:
                try:
                    telegram_send.send([report_message])
                except:
                    # TODO: why? not running this code locally anymore
                    pass
    if len(jobs) == 0:
        return
    if config.consecutive_jobs:
        for i, job in enumerate(reversed(jobs)):
            for job_prev in jobs[:-i - 1]:
                job.add_previous_job(job_prev)
    # running the jobs
    manage(jobs, telegram_callback)
    print('All the jobs were executed')
