import os

from runtools.utils import config
from job.manager import manage


def run_local(exp_name, args, script, args_file, seed=None, render=False):
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


def run_cluster(exp_name, args, script, args_file, seed, nb_seeds, job_class):
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
    # running the job
    manage([job_class([exp_name, script, args])], only_initialization=False, sleep_duration=1)
    print('...\n...\n...')
