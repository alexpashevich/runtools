from __future__ import absolute_import
from job.job_meta import JobMeta
from settings import GPU_MACHINE, CPU_MACHINE, SHARED_CPU_MACHINE


class JobGPU(JobMeta):
    def __init__(self, run_argv, interpreter='python'):
        JobMeta.__init__(self, run_argv)
        self.machine_name = GPU_MACHINE
        self.interpreter = interpreter
        # self.own_p_options = ['not gpumodel=\'\"\'\"\'gtx1080\'\"\'\"\'']
        self.own_p_options = ['']

    @property
    def oarsub_p_options(self):
        # return JobMeta(self).oarsub_p_options + ['not host=\'\"\'\"\'gpuhost13\'\"\'\"\'']
        # return JobMeta(self).oarsub_p_options + ['gpumodel=\'\"\'\"\'titan_x_pascal\'\"\'\"\' or gpumodel=\'\"\'\"\'titan_x\'\"\'\"\' or gpumodel=\'\"\'\"\'gtx1080_ti\'\"\'\"\' or gpumodel=\'\"\'\"\'titan_xp\'\"\'\"\'']
        # return JobMeta(self).oarsub_p_options
        return self.own_p_options


class JobCPU(JobMeta):
    def __init__(self, run_argv, interpreter='python'):
        JobMeta.__init__(self, run_argv)
        self.machine_name = CPU_MACHINE
        self.interpreter = interpreter
        self.own_p_options = ['cluster= \'\"\'\"\'ubuntu\'\"\'\"\'']

    @property
    def oarsub_p_options(self):
        return self.own_p_options



class JobSharedCPU(JobMeta):
    def __init__(self, run_argv, interpreter='python'):
        JobMeta.__init__(self, run_argv)
        self.machine_name = SHARED_CPU_MACHINE
        self.interpreter = interpreter
        self.own_p_options = ['cluster=\'\"\'\"\'thoth\'\"\'\"\'']

    @property
    def oarsub_p_options(self):
        return self.own_p_options
        # return JobMeta(self).oarsub_p_options + ['cluster=\'\"\'\"\'thoth\'\"\'\"\' and (host=\'\"\'\"\'node40-thoth.inrialpes.fr\'\"\'\"\' or host=\'\"\'\"\'node41-thoth.inrialpes.fr\'\"\'\"\' or host=\'\"\'\"\'node42-thoth.inrialpes.fr\'\"\'\"\' or host=\'\"\'\"\'node43-thoth.inrialpes.fr\'\"\'\"\' or host=\'\"\'\"\'node44-thoth.inrialpes.fr\'\"\'\"\')']
