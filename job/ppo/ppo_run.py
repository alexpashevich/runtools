import os
import sys
import shutil
import argparse
import datetime

from job.job_machine import JobCPU, JobGPU, JobSharedCPU
from settings import HOME
from pytools.tools import cmd
from job.job_manager import manage

SCRIPTS_PATH = os.path.join(HOME, 'Scripts')
RENDERED_ENVS_PATH = '/home/thoth/apashevi/Code/rlgrasp/rendered_envs.py'
TIMESTAMP = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')


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


def append_args(args, extra_args):
    for extra_arg in extra_args:
        arg_key = extra_arg[:extra_arg.find('=')+1]
        if arg_key in args:
            begin_arg = args.find(arg_key)
            end_arg = args[begin_arg:].find(' ')
            args = args[:begin_arg] + extra_arg + args[begin_arg+end_arg:]
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


def create_link(args_file, exp_name):
    _, exp_name_orig, _ = read_args(args_file)
    cache_dir = os.path.join("/scratch/gpuhost7/apashevi/Cache/Code/", exp_name_orig)
    link = os.path.join("/scratch/gpuhost7/apashevi/Cache/Links/", exp_name)
    if os.path.exists(link):
        os.unlink(link)
    os.symlink(cache_dir, link)


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
        raise ValueError('logdir is already specified in the file')
    return args


def run_job_cluster(args_file, seed, nb_seeds, job_class, extra_args):
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
        args += ' --timestamp={}'.format(TIMESTAMP)
    # creating symbolik link to the folder with code
    create_link(args_file, exp_name)
    # running the job
    manage([job_class([exp_name, args])], only_initialization=False, sleep_duration=3)
    print('...\n...\n...\n')


def run_job_local(args_file, extra_args):
    args, exp_name, _ = read_args(args_file)
    args = append_args(args, extra_args)
    # log dir creationg
    seed = 0
    args = create_log_dir(args, exp_name, seed)
    # TODO: delete timestamp from here
    if '--timestamp=' not in args:
        args += ' --timestamp={}'.format(TIMESTAMP)
    # running the script
    os.chdir('/home/thoth/apashevi/Code/agents/')
    script = 'python3 -m agents.scripts.train ' + args
    print('Running:\n' + script)
    os.system(script)


# def check_rendered_envs_file():
#     with open(RENDERED_ENVS_PATH) as pyfile:
#         content = pyfile.read()
#         if content.replace('\n', '') == 'rendered_envs = []; reported_envs = []':
#             return True
#         return False

def rewrite_rendered_envs_file(make_render=False):
    rendered_ids = '1' if make_render else ''
    content = 'rendered_envs = [{}]; reported_envs = []'.format(rendered_ids)
    with open(RENDERED_ENVS_PATH, 'r+') as pyfile:
        pyfile.seek(0)
        pyfile.write(content)
        pyfile.truncate()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=str,
                        help='File with argument to feed into the PPO training')
    # extra args provided in format "num_agents=8" (without two dashes)
    parser.add_argument('extra_args', type=str, nargs='*',
                        help='Additional arguments to be appended to the config arg.')
    parser.add_argument('-n', '--nb_seeds', type=int, default=1, required=False,
                        help='Number of seeds to run training with')
    parser.add_argument('-f', '--first_seed', type=int, default=1, required=False,
                        help='First seed value')
    parser.add_argument('-l', '--local', type=bool, default=False, required=False,
                        help='Whether to run the training locally or on clear')
    parser.add_argument('-s', '--shared', type=bool, default=False, required=False,
                        help='Whether to run the training on access1-sp')
    parser.add_argument('-e', '--edgar', type=bool, default=False, required=False,
                        help='Whether to run the training on edgar')
    parser.add_argument('-r', '--render', type=bool, default=False, required=False,
                        help='Whether to render the run (will run locally)')
    parser.add_argument('-b', '--besteffort', type=bool, default=False, required=False,
                        help='Whether to run in besteffort mode')
    parser.add_argument('-c', '--nb_cores', type=int, default=8, required=False,
                        help='Number of cores to be used on the cluster')
    parser.add_argument('-w', '--wallclock', type=int, default=72, required=False,
                        help='Job wall clock time to be set on the cluster')
    # parser.add_argument('--tf14', type=bool, default=True, required=False,
    #                     help='Whether to run the code using the updated tensorflow')

    args = parser.parse_args()

    if args.render:
        rewrite_rendered_envs_file(make_render=True)
    else:
        rewrite_rendered_envs_file(make_render=False)
    if args.shared and args.edgar:
        print('ERROR: both --edgar and --shared are True')
        return

    if args.edgar:
        parent_job = JobGPU
        l_options = ['walltime={}:0:0'.format(args.wallclock)]
    else:
        if args.shared:
            parent_job = JobSharedCPU
        else:
            parent_job = JobCPU
        l_options = ['nodes=1/core={},walltime={}:0:0'.format(args.nb_cores, args.wallclock)]

    class JobPPO(parent_job):
        def __init__(self, run_argv):
            parent_job.__init__(self, run_argv)
            self.global_path_project = SCRIPTS_PATH
            self.local_path_exe = 'ppo_mini.sh' if not args.shared else 'ppo_mini_tf14.sh'
            self.job_name = run_argv[0]
            self.interpreter = ''
            self.besteffort = args.besteffort
        @property
        def oarsub_l_options(self):
            return parent_job(self).oarsub_l_options + l_options

    create_parent_log_dir(args.file)
    cache_code_dir(args.file)
    if args.local or args.render:
        run_job_local(args.file, args.extra_args)
        if args.render:
            rewrite_rendered_envs_file(make_render=False)
    else:
        for seed in range(args.first_seed, args.first_seed + args.nb_seeds):
            run_job_cluster(args.file, seed, args.nb_seeds, JobPPO, args.extra_args)

if __name__ == '__main__':
    main()
