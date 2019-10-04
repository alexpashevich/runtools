import os

from job.job_machine import JobGPU, JobSharedCPU
from settings import HOME

ALLOWED_MODES = ('local', 'render', 'access2-cp', 'edgar', 'gce')
SCRIPTS_PATH = os.path.join(HOME, 'Scripts')


def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise TypeError('Boolean value expected.')


def print_ckpt(path):
    from tensorflow.python.tools.inspect_checkpoint import print_tensors_in_checkpoint_file
    print_tensors_in_checkpoint_file(file_name=path, tensor_name='', all_tensors=False)


def get_shared_machines_p_option(mode, machines):
    # return ' host=\'\"\'\"\'gpuhost10\'\"\'\"\''
    if mode != 'access2-cp':
        # return 'not host=\'\"\'\"\'gpuhost23\'\"\'\"\' and not host=\'\"\'\"\'gpuhost24\'\"\'\"\' and not host=\'\"\'\"\'gpuhost25\'\"\'\"\' and not host=\'\"\'\"\'gpuhost26\'\"\'\"\' and not host=\'\"\'\"\'gpuhost27\'\"\'\"\' and gpumem>11000'
        return 'not host=\'\"\'\"\'gpuhost20\'\"\'\"\' and not host=\'\"\'\"\'gpuhost21\'\"\'\"\' and not host=\'\"\'\"\'gpuhost22\'\"\'\"\' and not host=\'\"\'\"\'gpuhost23\'\"\'\"\' and not host=\'\"\'\"\'gpuhost24\'\"\'\"\' and not host=\'\"\'\"\'gpuhost25\'\"\'\"\' and not host=\'\"\'\"\'gpuhost26\'\"\'\"\' and not host=\'\"\'\"\'gpuhost27\'\"\'\"\' and gpumem>11000'
        # return 'not gpumodel=\'\"\'\"\'titan_rtx\'\"\'\"\' and not gpumodel=\'\"\'\"\'rtx2080_ti\'\"\'\"\' and gpumem>11000'
        # return ''
    # old machines can not run tensorflow >1.5
    nodes = {'s': list(range(1, 15)) + [36],
             'f': list(range(21, 36)) + list(range(37, 35)) + list(range(51, 55))}
    if machines == 's':
        hosts = 'cast(substring(host from \'\"\'\"\'node(.+)-\'\"\'\"\') as int) BETWEEN 1 AND 14'
    elif machines == 'f':
        hosts = 'cast(substring(host from \'\"\'\"\'node(.+)-\'\"\'\"\') as int) BETWEEN 21 AND 54'
    else:
        raise ValueError('machines descired type {} is unknown'.format(machines))
    return ' and ({})'.format(hosts)


def get_mode(config):
    if config.mode in ALLOWED_MODES:
        mode = config.mode
    elif config.mode in [mode[0] for mode in ALLOWED_MODES]:
        mode = [mode for mode in ALLOWED_MODES if mode[0] == config.mode][0]
    else:
        raise ValueError('mode {} is not allowed, available modes: {}'.format(config.mode, ALLOWED_MODES))
    if mode == 'gce':
        assert not (config.gce_id and mode != 'gce')
    return mode


def get_job(cluster, p_options, besteffort=False, nb_cores=8, wallclock=None):
    wallclock = 72 if wallclock is None else wallclock
    if cluster == 'edgar':
        parent_job = JobGPU
        time = '{}:0:0'.format(wallclock) if isinstance(wallclock, int) else wallclock
        l_options = ['walltime={}:0:0'.format(time)]
    elif cluster == 'access2-cp':
        parent_job = JobSharedCPU
        time = '{}:0:0'.format(wallclock) if isinstance(wallclock, int) else wallclock
        l_options = ['nodes=1/core={},walltime={}'.format(nb_cores, time)]
    else:
        raise ValueError('unknown cluster = {}'.format(cluster))

    class JobCluster(parent_job):
        def __init__(self, run_argv, p_options):
            parent_job.__init__(self, run_argv)
            self.global_path_project = SCRIPTS_PATH
            self.local_path_exe = 'run_with_pytorch.sh'
            self.job_name = run_argv[0]
            self.interpreter = ''
            self.besteffort = besteffort
            self.own_p_options = [parent_job(self).own_p_options[0] + p_options]
        @property
        def oarsub_l_options(self):
            return parent_job(self).oarsub_l_options + l_options
    return lambda run_argv: JobCluster(run_argv, p_options)


def get_gce_instance_ip(gce_id):
    # we assume gce_id >= 1
    return os.environ['GINSTS'].split('\x1e')[gce_id-1]
