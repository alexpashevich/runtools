from __future__ import absolute_import
from run.run_meta import RunMeta
from settings import GPU_MACHINE, CPU_MACHINE


class RunGPU(RunMeta):
    def __init__(self, run_argv, interpreter='python'):
        RunMeta.__init__(self, run_argv)
        self.machine_name = GPU_MACHINE
        self.interpreter = interpreter


class RunCPU(RunMeta):
    def __init__(self, run_argv, interpreter='python'):
        RunMeta.__init__(self, run_argv)
        self.machine_name = CPU_MACHINE
        self.interpreter = interpreter

    @property
    def oarsub_options(self):
        return RunMeta(self).oarsub_options + ' -p "cluster= \'\"\'\"\'ubuntu\'\"\'\"\'" '

