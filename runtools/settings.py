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
    'alfred.train.train': 'exp.name',
    'alfred.train.run': 'exp.name',
    'alfred.train.dagger': 'exp.name',
    'alfred.eval.eval_seq2seq': 'exp.name',
    'alfred.eval.leaderboard': 'exp.name',
    'alfred.data.create_lmdb': 'args.data_output',
    'alfred.data.process_tests': 'args.data_output',
    'alfred.gen.scripts.augment_trajectories': 'args.data_to',
    'alfred.gen.scripts.generate_trajectories': 'args.name',
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

# Scripts to debug mode args mapping
SCRIPT_TO_DEBUG_ARGS = {
   'rlons.scripts.collect': 'collect.workers=0',
   'rlons.scripts.train': 'train.workers=0',
   'alfred.train.train': 'exp.num_workers=0',
   'alfred.train.run': 'exp.num_workers=0',
   'alfred.train.dagger': 'exp.num_workers=0 dagger.num_workers=0',
   'alfred.eval.eval_seq2seq': 'exp.num_workers=0',
   'alfred.eval.leaderboard': 'exp.num_workers=0',
   'alfred.gen.scripts.augment_trajectories': 'args.num_threads=0',
   'alfred.data.create_lmdb': 'args.num_workers=0',
   'detection.train': 'args.num_workers=0',
}

# Scripts to fast epoch mode args mapping
SCRIPT_TO_FAST_EPOCH_ARGS = {
   'alfred.train.train': 'exp.fast_epoch=True',
   'alfred.train.run': 'exp.fast_epoch=True',
   'alfred.train.dagger': 'exp.fast_epoch=True',
   'alfred.eval.eval_seq2seq': 'exp.fast_epoch=True',
   'alfred.eval.leaderboard': 'exp.fast_epoch=True',
   'alfred.data.create_lmdb': 'args.fast_epoch=True',
   'detection.train': 'args.fast_epoch=True',
}

USED_CODE_DIRS = ('alfred', 'alftools')
ALLOWED_MODES = ('local', 'render', 'access2-cp', 'edgar', 'gcp')

# settings to control jobs restarting (if they are crashed or not making progress)
SCRIPT_TO_PROGRESS_WAIT_TIME = {
    'alfred.train.train': 3*60*60, # 3 hours
    'alfred.train.run': 3*60*60, # 3 hours
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
