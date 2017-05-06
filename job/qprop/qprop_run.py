from run.job_machine import JobCPU
import os, sys
from settings import HOME
from pytools.tools import cmd
import shutil

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


def create_success_report_dir(args, exp_name):
    if '--success_report_dir=' not in args:
        print('setting success_report_dir')
        success_report_dir = os.path.join('/scratch/gpuhost7/apashevi/Logs/success-logs/', exp_name)
        args += '--success_report_dir=' + success_report_dir + ' '
        if not os.path.exists(success_report_dir):
            os.makedirs(success_report_dir)
        else:
            for f in os.listdir(success_report_dir):
                f_path = os.path.join(success_report_dir, f)
                shutil.rmtree(f_path)
    return args


def parse_args_file(args_file):
    args, exp_name, overwrite = read_args(args_file)
    args, overwrite = create_temp_dir(args, exp_name, overwrite)
    args = create_outworlds_dir(args, exp_name)
    args = create_success_report_dir(args, exp_name)
    return args, exp_name


class RunQprop(JobCPU):
    def __init__(self, run_argv):
        JobCPU.__init__(self, run_argv, interpreter='')
        self.path_exe = os.path.join(SCRIPTS_PATH, 'qprop_mini.sh')
        self.job_name = run_argv[0]

    @property
    def oarsub_options(self):
        return JobCPU(self).oarsub_options + ' -l "nodes=1/core=32,walltime=24:0:0"'

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python3 script.py <args_file>')

    args, exp_name = parse_args_file(sys.argv[1])
    RunQprop([exp_name, args]).run()
