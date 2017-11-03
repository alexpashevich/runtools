import os
import shutil
import sys
from copy import copy

from pytools.tools import cmd
from job.job_manager import manage
from settings import CODE_DIRNAME

RENDERED_ENVS_PATH = '/home/thoth/apashevi/Code/rlgrasp/rendered_envs.py'

def read_args(args_file):
    with open(args_file) as f:
        args_list = f.read().splitlines()
    args = ''
    exp_name = 'default'
    overwrite = False
    for line in args_list:
        if line[0] == '#':
            continue
        if ' ' in line:
            print('WARNING: space(s) was found in {}, erased'.format(line))
            line = line.replace(' ', '')
        args += line + ' '
        if '--exp=' in line:
            exp_name = line[line.find('--exp=') + len('--exp='):]
        if '--overwrite=True' in line:
            overwrite = True
    return args, exp_name, overwrite


def get_arg_val_idxs(args, arg_key):
    begin_idx = args.find(arg_key)
    end_idx = args[begin_idx:].find(' ')
    if end_idx == -1:
        end_idx = len(args) - begin_idx
    return begin_idx+len(arg_key), begin_idx+end_idx


def append_args(args, extra_args):
    for extra_arg in extra_args:
        arg_key = extra_arg[:extra_arg.find('=')+1]
        if arg_key in args:
            begin_idx, end_idx = get_arg_val_idxs(args, arg_key)
            args = args[:begin_idx] + extra_arg + args[end_idx:]
        else:
            args += ' --' + extra_arg
    return args


def cache_code_dir(args_file):
    _, exp_name, _ = read_args(args_file)
    cache_dir = os.path.join("/scratch/gpuhost7/apashevi/Cache/Code/", exp_name)
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    os.makedirs(cache_dir)
    cmd('cp -R /home/thoth/apashevi/Code/rlgrasp {}/'.format(cache_dir))
    cmd('cp -R /home/thoth/apashevi/Code/agents {}/'.format(cache_dir))


def create_parent_log_dir(args_file):
    _, exp_name, _ = read_args(args_file)
    print('exp_name is {}'.format(exp_name))
    log_dir = os.path.join("/scratch/gpuhost7/apashevi/Logs/agents", exp_name)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)


def create_log_dir(args, exp_name, seed):
    if '--logdir=' not in args:
        log_dir = os.path.join("/scratch/gpuhost7/apashevi/Logs/agents", exp_name, 'seed%d' % seed)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        args += ' --logdir=' + log_dir
    else:
        print('WARNING: logdir is already specified in the file')
    return args


def run_job_cluster(args_file, seed, nb_seeds, job_class, extra_args, timestamp):
    args, exp_name, _ = read_args(args_file)
    args = append_args(args, extra_args)
    # log dir creationg
    args = create_log_dir(args, exp_name, seed)
    # adding the seed to arguments and exp_name
    if '--seed=' not in args:
        args += ' --seed=%d' % seed
        exp_name += '-s%d' % seed
    else:
        if '--seed=' in args and nb_seeds > 1:
            raise ValueError(('gridsearch over seeds is launched while a seed is already' +
                              'specified in the argument file'))
    if '--timestamp=' not in args:
        args += ' --timestamp={}'.format(timestamp)
    # running the job
    manage([job_class([exp_name, args])], only_initialization=False, sleep_duration=3)
    print('...\n...\n...')


def run_job_local(args_file, extra_args):
    args, exp_name, _ = read_args(args_file)
    args = append_args(args, extra_args)
    # log dir creation
    seed = 0
    args = create_log_dir(args, exp_name, seed)
    os.chdir('/home/thoth/apashevi/Code/agents/')
    # running the script
    script = 'python3 -m agents.scripts.train ' + args
    print('Running:\n' + script)
    os.system(script)


def rewrite_rendered_envs_file(make_render=False, rendered_envs_path=RENDERED_ENVS_PATH):
    rendered_ids = '1' if make_render else ''
    content = 'rendered_envs = [{}]; reported_envs = []'.format(rendered_ids)
    with open(rendered_envs_path, 'r+') as pyfile:
        pyfile.seek(0)
        pyfile.write(content)
        pyfile.truncate()


def get_sys_path_clean():
    sys_path_clean = []
    for path in sys.path:
        if CODE_DIRNAME not in path:
            sys_path_clean.append(path)
    return sys_path_clean


def change_sys_path(sys_path_clean, logdir):
    sys.path = copy(sys_path_clean)
    exp_name = os.path.basename(os.path.normpath(logdir))
    cachedir = os.path.join("/scratch/gpuhost7/apashevi/Cache/Code/", exp_name)
    sys.path.append(os.path.join(cachedir, 'agents'))
    sys.path.append(os.path.join(cachedir, 'rlgrasp'))


def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise TypeError('Boolean value expected.')
