import os

# Personnal settings
LOGIN = 'apashevi'

# PATH settings
HOME = '/home/thoth/apashevi'
LOGDIR_PATH = os.path.join(HOME, 'Logs')
OAR_LOG_PATH = os.path.join(LOGDIR_PATH, 'oarsub')
OAR_SCRIPT_PATH = os.path.join(LOGDIR_PATH, 'script')
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
    'rlons.scripts.collect_demos': 'collect.folder',
    'rlons.scripts.collect_images': 'collect.folder',
    'rlons.scripts.train': 'model.name',
    'sim2real.train': 'sim2real.name'}

USED_CODE_DIRS = 'mime', 'rlons'
ALLOWED_MODES = ('local', 'render', 'access2-cp', 'edgar')
