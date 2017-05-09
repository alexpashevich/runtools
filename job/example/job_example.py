from run.job_machine import JobCPU
import os
from settings import HOME
from run.job_manager import manage

EXAMPLE_PATH = os.path.join(HOME, 'src/tools/run/example')


class JobExample(JobCPU):
    def __init__(self, run_argv):
        JobCPU.__init__(self, run_argv)
        self.global_path_project = EXAMPLE_PATH
        self.local_path_exe = 'path_exe_example.py'
        self.job_name = 'new_example'

    @property
    def oarsub_l_options(self):
        return JobCPU(self).oarsub_l_options + ['nodes=1/core=1,walltime=1:0:0']

if __name__ == '__main__':
    manage([JobExample([])], only_initialization=False)
