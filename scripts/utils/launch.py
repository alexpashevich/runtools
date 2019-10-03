import os
import subprocess

from job.job_manager import manage

from settings import HOME
from scripts.utils import parse, misc

LOGS_PATH = os.path.join(HOME, 'Logs')


def job_local(exp_name, args, script, args_file, seed=None, render=False):
    # log dir creation
    if seed is None:
        seed = 0
    # elif script != 'bc.train':
    elif script != 'rlons.scripts.train':
        # in bc training the seed arg is not used
        argname = 'collect.seed' if script != 'ppo.train.run' else 'general.seed'
        args = parse.append_args(args, ['{}={}'.format(argname, seed)], args_file)
    args = parse.append_log_dir(args, exp_name, seed, args_file, script)
    script = 'python3 -u -m {} {}'.format(script, args)
    if render:
        rendering_on = ' collect.render=True' if '.json' in args_file else ' --render'
        script += rendering_on
    print('Running:\n' + script)
    if not render and 'DISPLAY' in os.environ:
        del os.environ['DISPLAY']
    os.system(script)


def job_cluster(exp_name, args, script, args_file, seed, nb_seeds, job_class, timestamp):
    # log dir creation
    args = parse.append_log_dir(args, exp_name, seed, args_file, script)
    # adding the seed to arguments and exp_name
    if '.seed=' not in args:
        # if script != 'bc.train':
        if script != 'rlons.scripts.train':
            # in bc training the seed arg is not used
            argname = 'collect.seed' if script != 'ppo.train.run' else 'general.seed'
            args = parse.append_args(args, ['{}={}'.format(argname, seed)], args_file)
        exp_name += '-s%d' % seed
    else:
        if 'seed=' in args and nb_seeds > 1:
            raise ValueError(('gridsearch over seeds is launched while a seed is already' +
                              'specified in the argument file'))
    if 'log.timestamp=' not in args and script == 'ppo.train.run':
        args += ' log.timestamp={}'.format(timestamp)
    # running the job
    manage([job_class([exp_name, script, args])], only_initialization=False, sleep_duration=1)
    print('...\n...\n...')

def job_gce(exp_name, args, seed, nb_seeds, timestamp, gce_id):
    # log dir creation
    args = parse.append_log_dir(args, exp_name, seed)
    if '--seed=' not in args:
        args += ' --seed=%d' % seed
        exp_name += '-s%d' % seed
    else:
        if '--seed=' in args and nb_seeds > 1:
            raise ValueError(('gridsearch over seeds is launched while a seed is already' +
                              'specified in the argument file'))
    if '--timestamp=' not in args:
        args += ' --timestamp={}'.format(timestamp)
    # args += ' --logdir=/home/apashevi/Logs/agents/{}'.format(exp_name)
    # running the script
    ld_library_path = "export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/apashevi/.mujoco/mjpro150/bin"
    script_local = '{}; export PYTHONPATH=$HOME/Code/rlgrasp:$HOME/Code/agents; cd Code/agents; python3 -m agents.scripts.train {}'.format(ld_library_path, args)
    print('Running on gce-{}'.format(gce_id))
    print(script_local)
    logdir = os.path.join(LOGS_PATH, 'oarsub', exp_name)
    if not os.path.exists(logdir):
        os.makedirs(logdir)
    stdoutf = open(os.path.join(logdir, "t{}out".format(timestamp)), 'wb')
    stderrf = open(os.path.join(logdir, "t{}err".format(timestamp)), 'wb')
    ssh_ip = misc.get_gce_instance_ip(gce_id)
    sp = subprocess.Popen(
        ["ssh", ssh_ip, script_local],
        shell=False, stdout=stdoutf, stderr=stderrf)
    print('...\n...\n...')




