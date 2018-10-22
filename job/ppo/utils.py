import os
import shutil
import sys
import subprocess
import collections

from git import Git
from copy import copy

from pytools.tools import cmd
from job.job_manager import manage
from job.job_machine import JobCPU, JobGPU, JobSharedCPU
from settings import CODE_DIRNAME, HOME

SCRIPTS_PATH = os.path.join(HOME, 'Scripts')
LOGS_PATH = os.path.join(HOME, 'Logs')
# new for pytorch ppo
USED_CODE_DIRS = 'mime', 'ppo', 'bc'
ALLOWED_MODES = ('local', 'render', 'access1-cp', 'edgar', 'gce')

def read_args(args_file):
    with open(args_file) as f:
        args_list = f.read().splitlines()
    args = ''
    exp_name = None
    for line in args_list:
        if line[0] == '#':
            continue
        for char in {' ', '\t', '\n'}:
            if char in line:
                if char == ' ':
                    print('WARNING: char(s) \'{}\' was found in {} and erased'.format(char, line))
                line = line.replace(char, '')
        if line[:2] == '--':
            args += ' ' + line
        else:
            args += line
        if '--exp=' in line:
            exp_name = line[line.find('--exp=') + len('--exp='):]
    if exp_name is None:
        exp_name = get_file_name(args_file)
        # gridargs_suffix = gridargs.replace('=', '').replace('--', '').replace('.', 'd').replace(',', 'c').replace('-', 'm').replace(' ', '_').replace('[', '').replace(']', '')
        # exp_name += gridargs_suffix
    return args, exp_name


def get_file_name(args_file):
    exp_name = os.path.basename(args_file).split('.')[0]
    return exp_name


def get_exp_lists(config, first_exp_id=1):
    gridargs_list = get_gridargs_list(config.grid)
    exp_name_list, args_list, exp_meta_list = [], [], []
    for args_file in config.files:
        for i, gridargs in enumerate(gridargs_list):
            args, exp_name = read_args(args_file)
            args = append_args(args, gridargs)
            args = append_args(args, config.extra_args)
            if len(gridargs_list) > 1:
                # TODO: check if this exp does not exist yet
                exp_name += '_v' + str(i+first_exp_id)
            exp_name_list.append(exp_name)
            args_list.append(args)
            exp_meta_list.append(
                {'args_file': args_file, 'extra_args': append_args(gridargs, config.extra_args)})
    return exp_name_list, args_list, exp_meta_list


def get_arg_val_idxs(args, arg_key):
    begin_idx = args.find('--' + arg_key) + 2
    end_idx = args[begin_idx:].find(' ')
    if end_idx == -1:
        end_idx = len(args) - begin_idx
    return begin_idx, begin_idx+end_idx


def append_args(args, extra_args):
    if not extra_args and not args:
        return ''
    if not args or not extra_args:
        return args or extra_args
    if isinstance(extra_args, str):
        extra_args = extra_args.replace('--', '').strip().split(' ')
    for extra_arg in extra_args:
        arg_key = extra_arg[:extra_arg.find('=')+1]
        if ('--' + arg_key) in args:
            begin_idx, end_idx = get_arg_val_idxs(args, arg_key)
            args = args[:begin_idx] + extra_arg + args[end_idx:]
        else:
            args += ' --' + extra_arg
    return args


def cache_code_dir(
        exp_name, commit_agents, commit_grasp_env,
        sym_link=False, sym_link_to_exp=None):
    cache_dir = os.path.join("/scratch/gpuhost7/apashevi/Cache/Code/", exp_name)
    if os.path.exists(cache_dir):
        if not os.path.islink(cache_dir):
            shutil.rmtree(cache_dir)
        else:
            os.unlink(cache_dir)
    if not sym_link:
        os.makedirs(cache_dir)
        for code_dir in USED_CODE_DIRS:
            cmd('cp -R /home/thoth/apashevi/Code/{} {}/'.format(code_dir, cache_dir))
    else:
        if not sym_link_to_exp:
            sym_link_to = '/home/thoth/apashevi/Code'
        else:
            sym_link_to = os.path.join('/scratch/gpuhost7/apashevi/Cache/Code/', sym_link_to_exp)
        os.symlink(sym_link_to, cache_dir)
    if commit_agents is not None:
        checkout_repo(os.path.join(cache_dir, 'agents'), commit_agents)
    if commit_grasp_env is not None:
        checkout_repo(os.path.join(cache_dir, 'rlgrasp'), commit_grasp_env)


def create_parent_log_dir(exp_name):
    print('exp_name is {}'.format(exp_name))
    log_dir = os.path.join("/scratch/gpuhost7/apashevi/Logs/agents", exp_name)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)


def append_log_dir(args, exp_name, seed):
    if '--logdir=' not in args:
        log_dir = os.path.join("/home/apashevi/Logs/agents", exp_name, 'seed%d' % seed)
        args += ' --logdir=' + log_dir
    else:
        print('WARNING: logdir is already specified in the file')
    return args

def run_job_local(exp_name, args, seed=None):
    # log dir creation
    if seed is None:
        seed = 0
    else:
        args = append_args(args, ['seed={}'.format(seed)])
    args = append_log_dir(args, exp_name, seed)
    # os.chdir('/home/thoth/apashevi/Code/agents/')
    os.chdir('/home/thoth/apashevi/Code/ppo/')
    # running the script
    # script = 'python3 -m agents.scripts.train ' + args
    script = 'python3 main.py ' + args
    print('Running:\n' + script)
    os.system(script)


def run_job_cluster(exp_name, args, seed, nb_seeds, job_class, timestamp):
    # log dir creation
    args = append_log_dir(args, exp_name, seed)
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
    manage([job_class([exp_name, args])], only_initialization=False, sleep_duration=1)
    print('...\n...\n...')

def get_gce_instance_ip(gce_id):
    # we assume gce_id >= 1
    return os.environ['GINSTS'].split('\x1e')[gce_id-1]

def run_job_gce(exp_name, args, seed, nb_seeds, timestamp, gce_id):
    # log dir creation
    args = append_log_dir(args, exp_name, seed)
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
    ssh_ip = get_gce_instance_ip(gce_id)
    sp = subprocess.Popen(
        ["ssh", ssh_ip, script_local],
        shell=False, stdout=stdoutf, stderr=stderrf)
    print('...\n...\n...')


def get_sys_path_clean():
    sys_path_clean = []
    for path in sys.path:
        if CODE_DIRNAME not in path and CODE_DIRNAME.replace('thoth/', '') not in path:
            sys_path_clean.append(path)
    return sys_path_clean


def change_sys_path(sys_path_clean, logdir):
    sys.path = copy(sys_path_clean)
    exp_name = os.path.basename(os.path.normpath(logdir))
    cachedir = os.path.join("/scratch/gpuhost7/apashevi/Cache/Code/", exp_name)
    for code_dir in USED_CODE_DIRS:
        sys.path.append(os.path.join(cachedir, code_dir))


def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise TypeError('Boolean value expected.')

def get_job(cluster, p_options, script, besteffort=False, nb_cores=8, wallclock=None):
    if cluster == 'edgar':
        parent_job = JobGPU
        wallclock = 12 if wallclock is None else wallclock
        time = '{}:0:0'.format(wallclock) if isinstance(wallclock, int) else wallclock
        l_options = ['walltime={}:0:0'.format(time)]
    elif cluster == 'access1-cp':
        parent_job = JobSharedCPU
        wallclock = 72 if wallclock is None else wallclock
        time = '{}:0:0'.format(wallclock) if isinstance(wallclock, int) else wallclock
        l_options = ['nodes=1/core={},walltime={}'.format(nb_cores, time)]
    else:
        raise ValueError('unknown cluster = {}'.format(cluster))

    class JobPPO(parent_job):
        def __init__(self, run_argv, p_options):
            parent_job.__init__(self, run_argv)
            self.global_path_project = SCRIPTS_PATH
            self.local_path_exe = script
            self.job_name = run_argv[0]
            self.interpreter = ''
            self.besteffort = besteffort
            self.own_p_options = [parent_job(self).own_p_options[0] + p_options]
        @property
        def oarsub_l_options(self):
            return parent_job(self).oarsub_l_options + l_options
    return lambda run_argv: JobPPO(run_argv, p_options)

def print_ckpt(path):
    from tensorflow.python.tools.inspect_checkpoint import print_tensors_in_checkpoint_file
    print_tensors_in_checkpoint_file(file_name=path, tensor_name='', all_tensors=False)

def get_gridargs_list(grid):
    if not grid:
        return [None]
    gridargs_list = ['']
    grid_dict = collections.OrderedDict(sorted(grid.items()))
    for key, value_list in grid_dict.items():
        assert isinstance(value_list, list) or isinstance(value_list, tuple)
        new_gridargs_list = []
        for gridargs_old in gridargs_list:
            for value in value_list:
                if ' ' in str(value):
                    print('removed spaces from {}, it became {}'.format(
                        value, str(value).replace(' ', '')))
                gridarg = ' --{}={}'.format(key, str(value).replace(' ', ''))
                new_gridargs_list.append(gridargs_old + gridarg)
        gridargs_list = new_gridargs_list
    return gridargs_list

def checkout_repo(repo, commit_tag):
    g = Git(repo)
    g.checkout(commit_tag)
    print('checkouted {} to {}'.format(repo, commit_tag))

def get_shared_machines_p_option(mode, machines):
    if mode != 'access1-cp':
        return ''
    # old machines can not run tensorflow >1.5
    nodes = {'s': list(range(1, 15)) + [36],
             'f': list(range(21, 36)) + list(range(37, 35)) + list(range(51, 55))}
    if machines == 's':
        hosts = 'cast(substring(host from \'\"\'\"\'node(.+)-\'\"\'\"\') as int) BETWEEN 1 AND 14'
    elif machines == 'f':
        hosts = 'cast(substring(host from \'\"\'\"\'node(.+)-\'\"\'\"\') as int) BETWEEN 21 AND 54'
    else:
        raise ValueError('machines descired type {} is unknown'.format(machines))

    return ' and ({})'.format(hosts)


def get_mode(config):
    if config.mode in ALLOWED_MODES:
        mode = config.mode
    elif config.mode in [mode[0] for mode in ALLOWED_MODES]:
        mode = [mode for mode in ALLOWED_MODES if mode[0] == config.mode][0]
    else:
        raise ValueError('mode {} is not allowed, available modes: {}'.format(config.mode, ALLOWED_MODES))
    assert not (config.gce_id and mode != 'gce')
    return mode

