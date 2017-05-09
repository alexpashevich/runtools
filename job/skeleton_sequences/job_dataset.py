from run.job_machine import JobCPU
import os
from run.skeleton_sequences.job_deep_learning import SKELETON_SEQUENCES_PATH
from run.job_manager import manage

DATASET_WRITER_DIR = 'tensorflow_datasets'


class JobDataset(JobCPU):
    def __init__(self, run_argv):
        JobCPU.__init__(self, run_argv)
        self.global_path_project = SKELETON_SEQUENCES_PATH
        self.local_path_exe = os.path.join(DATASET_WRITER_DIR, 'dataset_generator.py')
        self.job_name = 'dali_translation'
        self.interpreter = 'python3'
        self.librairies_to_install = ['python3-scipy']

    @property
    def oarsub_l_options(self):
        return JobCPU(self).oarsub_l_options + ['nodes=1/core=32,walltime=20:0:0']

if __name__ == '__main__':
    manage([JobDataset([])], only_initialization=False)
