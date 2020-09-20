import os
import enum

# Personnal settings
LOGIN = 'pashevich'

# PATH settings
HOME = '/home/pashevich'
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
    'alfred.train.train_seq2seq': 'exp.name',
    'alfred.eval.eval_seq2seq': 'exp.name',
    'alfred.data.create_data': 'args.data_output',
    'alfred.gen.scripts.augment_trajectories': 'args.data_to',
    'contrastive.howto100m.train': 'exp.name',
    'contrastive.create_data': 'args.data_output',
    'detection.train': 'args.model_name',
    'detection.data.create': 'args.name',
    'rlons.scripts.collect': 'collect.folder',
    'rlons.scripts.train': 'train.model.name',
    'rlons.scripts.eval': 'train.model.name',
    'rlons.scripts.method': 'train.model.name',
    'rlons.scripts.sim2real': 'train.model.name'
}

USED_CODE_DIRS = ('alfred', 'alftools')
ALLOWED_MODES = ('local', 'render', 'access2-cp', 'edgar', 'gcp')

# settings to control jobs restarting (if they are crashed or not making progress)
SCRIPT_TO_PROGRESS_WAIT_TIME = {
    'alfred.train.train_seq2seq': 3*60*60, # 3 hours
    # 'alfred.train.train_seq2seq': 10, # 10 sec (for debug)
    'alfred.eval.eval_seq2seq': 20*60, # 10 minutes
    'alfred.gen.scripts.augment_trajectories': 10*60, # 10 minuties
}
MAX_TIMES_RESTART_CRASHED_JOB = 3


class JobStatus(enum.Enum):
   WAITING_PREVIOUS = 0
   READY_TO_START = 1
   SCHEDULED = 2
   RUNNING = 3
   STUCK = 4
   CRASHED = 5
   DONE_FAILURE = 6
   DONE_SUCCESS = 7
