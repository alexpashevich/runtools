import os
import shutil
import sys

from git import Git
from copy import copy

from pytools.tools import cmd
from job.job_manager import manage
from job.job_machine import JobCPU, JobGPU, JobSharedCPU
from settings import CODE_DIRNAME, HOME

SCRIPTS_PATH = os.path.join(HOME, 'Scripts')
RENDERED_ENVS_PATH = '/home/thoth/apashevi/Code/rlgrasp/rendered_envs.py'

def read_args(args_file, gridargs=None):
    with open(args_file) as f:
        args_list = f.read().splitlines()
    args = ''
    exp_name = None
    overwrite = False
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
        if '--overwrite=True' in line:
            overwrite = True
    if exp_name is None:
        exp_name = get_file_name(args_file)
    if gridargs is not None:
        # args += gridargs
        args = append_args(args, gridargs)
        gridargs_suffix = gridargs.replace('=', '').replace('--', '').replace('.', 'd').replace(',', 'c').replace('-', 'm').replace(' ', '_').replace('[', '').replace(']', '')
        exp_name += gridargs_suffix
    return args, exp_name, overwrite


def get_file_name(args_file):
    exp_name = os.path.basename(args_file).split('.')[0]
    return exp_name


def get_arg_val_idxs(args, arg_key):
    begin_idx = args.find('--' + arg_key) + 2
    end_idx = args[begin_idx:].find(' ')
    if end_idx == -1:
        end_idx = len(args) - begin_idx
    return begin_idx, begin_idx+end_idx


def stringify_extra_args(extra_args):
    # create a string out of a list of arguments
    if len(extra_args) == 0:
        return None
    return ' --' + ' --'.join(extra_args)


def append_args(args, extra_args):
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


def cache_code_dir(args_file, commit_agents, commit_grasp_env, gridargs=None, sym_link=False):
    _, exp_name, _ = read_args(args_file, gridargs)
    cache_dir = os.path.join("/scratch/gpuhost7/apashevi/Cache/Code/", exp_name)
    if os.path.exists(cache_dir):
        if not os.path.islink(cache_dir):
            shutil.rmtree(cache_dir)
        else:
            os.unlink(cache_dir)
    if not sym_link:
        os.makedirs(cache_dir)
        cmd('cp -R /home/thoth/apashevi/Code/rlgrasp {}/'.format(cache_dir))
        cmd('cp -R /home/thoth/apashevi/Code/agents {}/'.format(cache_dir))
    else:
        os.symlink('/home/thoth/apashevi/Code', cache_dir)
    if commit_agents is not None:
        checkout_repo(os.path.join(cache_dir, 'agents'), commit_agents)
    if commit_grasp_env is not None:
        checkout_repo(os.path.join(cache_dir, 'rlgrasp'), commit_grasp_env)


def create_parent_log_dir(args_file, gridargs=None):
    _, exp_name, _ = read_args(args_file, gridargs)
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


def run_job_cluster(
        args_file, seed, nb_seeds, job_class, timestamp, gridargs=None, not_in_name_args=None):
    args, exp_name, _ = read_args(args_file, gridargs)
    # args = append_args(args, extra_args)
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
    if not_in_name_args:
        args += ' ' + not_in_name_args
    # running the job
    manage([job_class([exp_name, args])], only_initialization=False, sleep_duration=3)
    print('...\n...\n...')


def run_job_local(args_file, extra_args, seed=None, not_in_name_args=None):
    args, exp_name, _ = read_args(args_file, extra_args)
    # log dir creation
    if seed is None:
        seed = 0
    else:
        args = append_args(args, ['seed={}'.format(seed)])
    args = create_log_dir(args, exp_name, seed)
    if not_in_name_args:
        args += ' ' + not_in_name_args
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

def get_job(cluster, p_options, besteffort=False, nb_cores=8, wallclock=None, use_tf15=False):
    if not use_tf15:
        path_exe = 'ppo_mini.sh'
    else:
        path_exe = 'ppo_mini_tf15ucpu.sh'
    if cluster == 'edgar':
        # if not use_tf15:
        #     path_exe = 'ppo_mini.sh'
        # else:
        #     path_exe = 'ppo_mini_tf15.sh'
        parent_job = JobGPU
        wallclock = 12 if wallclock is None else wallclock
        l_options = ['walltime={}:0:0'.format(wallclock)]
    elif cluster == 'access1-cp':
        # if not use_tf15:
        #     path_exe = 'ppo_mini_cpu.sh'
        # else:
        #     path_exe = 'ppo_mini_tf15ucpu.sh'
        parent_job = JobSharedCPU
        wallclock = 72 if wallclock is None else wallclock
        l_options = ['nodes=1/core={},walltime={}:0:0'.format(nb_cores, wallclock)]
    else:
        raise ValueError('unknown cluster = {}'.format(cluster))

    class JobPPO(parent_job):
        def __init__(self, run_argv, p_options):
            parent_job.__init__(self, run_argv)
            self.global_path_project = SCRIPTS_PATH
            self.local_path_exe = path_exe
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

def gridargs_list(grid_dict):
    gridargs_list = ['']
    assert isinstance(grid_dict, dict)
    for key, value_list in grid_dict.items():
        assert isinstance(value_list, list) or isinstance(value_list, tuple)
        new_gridargs_list = []
        for gridargs_old in gridargs_list:
            for value in value_list:
                gridarg = ' --{}={}'.format(key, value)
                new_gridargs_list.append(gridargs_old + gridarg)
        gridargs_list = new_gridargs_list
    return gridargs_list

def checkout_repo(repo, commit_tag):
    g = Git(repo)
    g.checkout(commit_tag)
    print('checkouted {} to {}'.format(repo, commit_tag))

def get_shared_machines_p_option(category):
    # nodes = {'s': list(range(1, 15)) + [36], 'f': list(range(21, 36)) + list(range(37, 45))}
    nodes = {'s': list(range(1, 15)), 'f': list(range(21, 45))}
    assert category in nodes.keys()
    nodes_indices = nodes[category]
    hosts = []
    for node_idx in nodes_indices:
        hosts.append('host=\'\"\'\"\'node{}-thoth.inrialpes.fr\'\"\'\"\''.format(node_idx))
    p_option = ' or '.join(hosts)
    return ' and ({})'.format(p_option)
