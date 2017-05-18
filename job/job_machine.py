from __future__ import absolute_import
from job.job_meta import JobMeta
from settings import GPU_MACHINE, CPU_MACHINE


class JobGPU(JobMeta):
    def __init__(self, run_argv, interpreter='python'):
        JobMeta.__init__(self, run_argv)
        self.machine_name = GPU_MACHINE
        self.interpreter = interpreter

    @property
    def oarsub_p_options(self):
        return JobMeta(self).oarsub_p_options + ['not host=\'\"\'\"\'gpuhost6\'\"\'\"\'']


class JobCPU(JobMeta):
    def __init__(self, run_argv, interpreter='python'):
        JobMeta.__init__(self, run_argv)
        self.machine_name = CPU_MACHINE
        self.interpreter = interpreter

    @property
    def oarsub_p_options(self):
        return JobMeta(self).oarsub_p_options + ['cluster= \'\"\'\"\'ubuntu\'\"\'\"\'']

