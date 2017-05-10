from job.job_machine import JobGPU, JobCPU
import sys, os

SKELETON_SEQUENCES_PATH = '/home/lear/erleroux/src/skeleton_sequences'
MAIN_DIR = 'tensorflow_main'


def train_val_test_runs(train_run_argv, evaluation_run_argv, job_name, machine='gpu', only_evaluating=False):
    # validation_run_argv = evaluation_run_argv + ['evaluation_name=validation']
    # validation_run = JobCPUEvaluation(validation_run_argv, job_name)
    # validation_run.add_previous_job(train_run)
    test_run_argv = evaluation_run_argv + ['evaluation_name=test', 'top_n_to_test=3']
    if machine == 'gpu':
        train_run = JobGPUTrain(train_run_argv, job_name)
    else:
        train_run = JobCPUTrain(train_run_argv, job_name)
    test_run = JobCPUEvaluation(test_run_argv, job_name)
    # Add dependencies
    if only_evaluating:
        return [test_run]
    else:
        test_run.add_previous_job(train_run)
        return [train_run, test_run]


class JobGPUTrain(JobGPU):
    def __init__(self, run_argv, job_name):
        JobGPU.__init__(self, run_argv)
        self.interpreter = 'python3'  # tensorflow installed with python3
        self.global_path_project = SKELETON_SEQUENCES_PATH
        self.local_path_exe = os.path.join(MAIN_DIR, 'train.py')
        self.job_name = job_name

    @property
    def oarsub_l_options(self):
        return JobGPU(self).oarsub_l_options + ['walltime=48:0:0']

    # @property
    # def oarsub_p_options(self):
    #     return JobGPU(self).oarsub_p_options + ['gpumem>3000']


class JobCPUTrain(JobCPU):
    def __init__(self, run_argv, job_name):
        JobCPU.__init__(self, run_argv)
        self.interpreter = 'python3'  # tensorflow installed with python3
        self.global_path_project = SKELETON_SEQUENCES_PATH
        self.local_path_exe = os.path.join(MAIN_DIR, 'train.py')
        self.job_name = job_name

    @property
    def oarsub_l_options(self):
        return JobCPU(self).oarsub_l_options + ['nodes=1/core=8,walltime=48:0:0']


class JobCPUEvaluation(JobCPU):
    def __init__(self, run_argv, job_name):
        JobCPU.__init__(self, run_argv)
        self.interpreter = 'python3'  # tensorflow installed with python3
        self.global_path_project = SKELETON_SEQUENCES_PATH
        self.local_path_exe = os.path.join(MAIN_DIR, 'evaluation.py')
        self.job_name = job_name

    @property
    def oarsub_l_options(self):
        return JobCPU(self).oarsub_l_options + ['nodes=1/core=8,walltime=2:0:0']
