from run.run_machine import RunCPU
import os
from settings import HOME

# Enable to parallelize, and accelerate the creation of datasets
SKELETON_SEQUENCE_DATASET_WRITER_PATH = os.path.join(HOME, 'src/skeleton_sequences/skeleton_webpage/dataset_webpage')


class RunDataset(RunCPU):
    def __init__(self, run_argv):
        RunCPU.__init__(self, run_argv)
        self.path_exe = os.path.join(SKELETON_SEQUENCE_DATASET_WRITER_PATH, 'dataset_html.py')
        self.job_name = 'webpage_skeleton'
        self.interpreter = 'python3'

    @property
    def oarsub_options(self):
        return RunCPU(self).oarsub_options + ' -l "nodes=1/core=8,walltime=12:0:0"'


if __name__ == '__main__':
    RunDataset([]).run()
