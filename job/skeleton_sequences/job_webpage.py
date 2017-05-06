from run.job_machine import JobCPU
import os
from run.job_manager import manage
from run.skeleton_sequences.job_deep_learning import SKELETON_SEQUENCES_PATH

WEBPAGE_DIR = 'skeleton_webpage/dataset_webpage'


class RunDataset(JobCPU):
    def __init__(self, run_argv):
        JobCPU.__init__(self, run_argv)
        self.global_path_project = SKELETON_SEQUENCES_PATH
        self.local_path_exe = os.path.join(WEBPAGE_DIR, 'dataset_html.py')
        self.job_name = 'webpage_skeleton'
        self.interpreter = 'python3'

    @property
    def oarsub_options(self):
        return JobCPU(self).oarsub_options + ' -l "nodes=1/core=8,walltime=12:0:0"'


if __name__ == '__main__':
    manage([RunDataset([])])
