from __future__ import absolute_import
from runtools.job.meta import JobMeta
from runtools.settings import GPU_MACHINE, CPU_MACHINE


class JobGPU(JobMeta):
    def __init__(self, run_argv, interpreter='python'):
        JobMeta.__init__(self, run_argv)
        self.machine_name = GPU_MACHINE
        self.interpreter = interpreter
        self.own_p_options = ['']

    @property
    def oarsub_p_options(self):
        return self.own_p_options


class JobCPU(JobMeta):
    def __init__(self, run_argv, interpreter='python'):
        JobMeta.__init__(self, run_argv)
        self.machine_name = CPU_MACHINE
        self.interpreter = interpreter
        self.own_p_options = ['cluster=\'\"\'\"\'thoth\'\"\'\"\'']

    @property
    def oarsub_p_options(self):
        return self.own_p_options
