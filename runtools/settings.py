import os

# Personnal settings
LOGIN = 'apashevi'

# PATH settings
HOME = '/home/apashevi'
LOGDIR_PATH = os.path.join(HOME, 'Logs')
OAR_LOG_PATH = os.path.join(LOGDIR_PATH, 'oarsub')
OAR_SCRIPT_PATH = os.path.join(LOGDIR_PATH, 'script')
MODEL_LOG_PATH = os.path.join(LOGDIR_PATH, 'agents')
CODEDIR_PATH = os.path.join(HOME, 'Code')
CACHEDIR_PATH = os.path.join(HOME, 'Cache')
SCRIPTS_PATH = os.path.join(HOME, 'Scripts')

# INRIA settings
CPU_MACHINE = 'access2-cp'
SHARED_CPU_MACHINE = 'access2-cp'
GPU_MACHINE = 'edgar'
MAX_DEFAULT_JOBS = {GPU_MACHINE: 1000, SHARED_CPU_MACHINE: 100000}
MAX_DEFAULT_CORES = {GPU_MACHINE: 1000, SHARED_CPU_MACHINE: 300000}
MAX_BESTEFFORT_CORES = {GPU_MACHINE: 1000, SHARED_CPU_MACHINE: 100000}

# Scripts to logdir mapping
SCRIPT_TO_LOGDIR = {
    'rlons.scripts.collect': 'collect.folder',
    'rlons.scripts.train': 'train.model.name',
    'rlons.scripts.eval': 'train.model.name',
    'rlons.scripts.method': 'train.model.name',
    'rlons.scripts.sim2real': 'train.model.name'}

USED_CODE_DIRS = 'unmake-rl', 'rlons'
ALLOWED_MODES = ('local', 'render', 'access2-cp', 'edgar')
