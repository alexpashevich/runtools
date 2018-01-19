from __future__ import absolute_import
from job.job_meta import JobMeta
from settings import GPU_MACHINE, CPU_MACHINE, SHARED_CPU_MACHINE


class JobGPU(JobMeta):
    def __init__(self, run_argv, interpreter='python'):
        JobMeta.__init__(self, run_argv)
        self.machine_name = GPU_MACHINE
        self.interpreter = interpreter

    @property
    def oarsub_p_options(self):
        # return JobMeta(self).oarsub_p_options + ['not host=\'\"\'\"\'gpuhost13\'\"\'\"\'']
        # return JobMeta(self).oarsub_p_options + ['gpumodel=\'\"\'\"\'titan_x_pascal\'\"\'\"\' or gpumodel=\'\"\'\"\'titan_x\'\"\'\"\' or gpumodel=\'\"\'\"\'gtx1080_ti\'\"\'\"\' or gpumodel=\'\"\'\"\'titan_xp\'\"\'\"\'']
        return JobMeta(self).oarsub_p_options


class JobCPU(JobMeta):
    def __init__(self, run_argv, interpreter='python'):
        JobMeta.__init__(self, run_argv)
        self.machine_name = CPU_MACHINE
        self.interpreter = interpreter

    @property
    def oarsub_p_options(self):
        # return JobMeta(self).oarsub_p_options + [('cluster= \'\"\'\"\'ubuntu\'\"\'\"\' and ' +
        #                                           'not host=\'\"\'\"\'node32\'\"\'\"\' and ' +
        #                                           'not host=\'\"\'\"\'node36\'\"\'\"\' and ' +
        #                                           'not host=\'\"\'\"\'node42\'\"\'\"\'')]
        return JobMeta(self).oarsub_p_options + ['cluster= \'\"\'\"\'ubuntu\'\"\'\"\'']



class JobSharedCPU(JobMeta):
    def __init__(self, run_argv, interpreter='python'):
        JobMeta.__init__(self, run_argv)
        self.machine_name = SHARED_CPU_MACHINE
        self.interpreter = interpreter

    @property
    def oarsub_p_options(self):
        return JobMeta(self).oarsub_p_options + ['cluster=\'\"\'\"\'thoth\'\"\'\"\'']
