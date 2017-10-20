from job.job_machine import JobCPU
import os, sys
from settings import HOME
from pytools.tools import cmd
import shutil
from job.job_manager import manage
SCRIPTS_PATH = os.path.join(HOME, 'Scripts')


def read_args(args_file):
    with open(args_file) as f:
        args_list = f.read().splitlines()
    args = ''
    exp_name = 'default'
    overwrite = False
    for line in args_list:
        args += line + ' '
        if '--exp=' in line:
            exp_name = line[line.find('--exp=') + len('--exp='):]
            print('exp_name is {}'.format(exp_name))
        if '--overwrite=True' in line:
            overwrite = True
            print('overwrite is True')
    return args, exp_name, overwrite


def create_temp_dir(args, exp_name, overwrite):
    temp_dir = os.path.join("/scratch/gpuhost7/apashevi/Temp/", exp_name)
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    else:
        if not overwrite:
            ans = input("Overwrite is set to False. You want to overwrite previous experiments?' (y/n)")
            if ans != 'y': sys.exit(0)
            overwrite = True
            if '--overwrite=False' in args:
                args.replace('--overwrite=False', '--overwrite=True')
            else:
                args += '--overwrite=True '
        for folder in os.listdir(temp_dir):
            folder_path = os.path.join(temp_dir, folder)
            shutil.rmtree(folder_path)
    cmd('cp -R /home/thoth/apashevi/Code/rlgrasp {}/'.format(temp_dir))
    cmd('cp -R /home/thoth/apashevi/Code/rllabplusplus {}/'.format(temp_dir))
    return args, overwrite


def create_outworlds_dir(args, exp_name):
    if '--outworlds_dir=' not in args:
        print('setting outworlds_dir')
        outworlds_dir = os.path.join('/scratch/gpuhost7/apashevi/Worlds/', exp_name)
        args += '--outworlds_dir=' + outworlds_dir + ' '
        if not os.path.exists(outworlds_dir):
            os.makedirs(outworlds_dir)
            os.makedirs(os.path.join(outworlds_dir, 'unsuccessful'))
    return args


def parse_args_file(args_file):
    args, exp_name, overwrite = read_args(args_file)
    args, overwrite = create_temp_dir(args, exp_name, overwrite)
    args = create_outworlds_dir(args, exp_name)
    return args, exp_name


class JobQprop(JobCPU):
    def __init__(self, run_argv):
        JobCPU.__init__(self, run_argv)
        self.global_path_project = SCRIPTS_PATH
        self.local_path_exe = 'qprop_mini.sh'
        self.job_name = run_argv[0]
        self.interpreter = ''

    @property
    def oarsub_l_options(self):
        return JobCPU(self).oarsub_l_options + ['nodes=1/core=8,walltime=72:0:0']

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python3 script.py <args_file>')

    args, exp_name = parse_args_file(sys.argv[1])
    manage([JobQprop([exp_name, args])], only_initialization=False, sleep_duration=3)
