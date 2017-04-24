from run.job_machine import JobGPU, JobCPU
import sys, os

SKELETON_SEQUENCES_PATH = '/home/lear/erleroux/src/skeleton_sequences'
MAIN_DIR = 'tensorflow_main'


def train_val_test_runs(train_run_argv, evaluation_run_argv, job_name, machine='gpu', only_evaluating=False):
    validation_run_argv = evaluation_run_argv + ['evaluation_name=validation']
    test_run_argv = evaluation_run_argv + ['evaluation_name=test', 'top_n_to_test=3']
    if machine == 'gpu':
        train_run = JobGPUTrain(train_run_argv, job_name)
    else:
        train_run = JobCPUTrain(train_run_argv, job_name)
    validation_run = JobCPUEvaluation(validation_run_argv, job_name)
    test_run = JobCPUEvaluation(test_run_argv, job_name)
    # Add dependencies
    test_run.add_previous_job(validation_run)
    if only_evaluating:
        return [validation_run, test_run]
    else:
        validation_run.add_previous_job(train_run)
        return [train_run, validation_run, test_run]


class JobGPUTrain(JobGPU):
    def __init__(self, run_argv, job_name):
        JobGPU.__init__(self, run_argv)
        self.interpreter = 'python3'  # tensorflow installed with python3
        self.global_path_project = SKELETON_SEQUENCES_PATH
        self.local_path_exe = os.path.join(MAIN_DIR, 'train.py')
        self.job_name = job_name

    @property
    def oarsub_l_options(self):
        return JobGPU(self).oarsub_l_options + ['walltime=24:0:0']


class JobCPUTrain(JobCPU):
    def __init__(self, run_argv, job_name):
        JobCPU.__init__(self, run_argv)
        self.interpreter = 'python3'  # tensorflow installed with python3
        self.global_path_project = SKELETON_SEQUENCES_PATH
        self.local_path_exe = os.path.join(MAIN_DIR, 'train.py')
        self.job_name = job_name

    @property
    def oarsub_l_options(self):
        return JobCPU(self).oarsub_options + ['nodes=1/core=4,walltime=2:0:0']


class JobCPUEvaluation(JobCPU):
    def __init__(self, run_argv, job_name):
        JobCPU.__init__(self, run_argv)
        self.interpreter = 'python3'  # tensorflow installed with python3
        self.global_path_project = SKELETON_SEQUENCES_PATH
        self.local_path_exe = os.path.join(MAIN_DIR, 'evaluate.py')
        self.job_name = job_name

    @property
    def oarsub_l_options(self):
        return super().oarsub_l_options + ['nodes=1/core=8,walltime=2:0:0']
