import os

# Personnal settings
EMAIL = '$surname.name@inria.fr'
LOGIN = 'erleroux'

# Directory settings
HOME = '/home/lear/erleroux'
PROJECT_ROOT = os.path.join(HOME, 'src/tools')
OAR_DIRNAME = os.path.join(HOME, 'OAR')
OARSUB_DIRNAME = os.path.join(OAR_DIRNAME, 'oarsub')
SCRIPT_DIRNAME = os.path.join(OAR_DIRNAME, 'script')

# INRIA settings
CPU_MACHINE = 'clear'
GPU_MACHINE = 'edgar'
MAX_DEFAULT_JOBS = {GPU_MACHINE: 2, CPU_MACHINE: 10}
