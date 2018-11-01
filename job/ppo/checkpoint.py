import os
import argparse

import tensorflow as tf

from job.ppo import utils
from job.job_manager import manage

def get_train_args(seed_path, timestamp, device):
    # we can pass the cuda arg as well
    _, seed_dir = os.path.split(os.path.normpath(seed_path))
    seed = seed_dir.replace('seed', '')
    train_args = '--logdir={} --timestamp={} --seed={}'.format(seed_path, timestamp, seed)
    if device:
        train_args += ' --device={}'.format(device)
    return train_args

def send_job(job, seed_path, timestamp, device, script):
    ''' Send a job to the cluster '''
    exp_path, seed_dir = os.path.split(os.path.normpath(seed_path))
    exp_name = os.path.basename(exp_path)
    seed = seed_dir.replace('seed', '')
    exp_name_seed = '{}-s{}'.format(exp_name, seed)
    train_args = get_train_args(seed_path, timestamp, device)
    manage([job([exp_name_seed, script, train_args])], only_initialization=False, sleep_duration=1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('exp_path', type=str, nargs='*',
                        help='Full experiment path (to the dir where the config is stored)')
    parser.add_argument('-nep', '--no_env_process', default=False, action='store_true',
                        help='Step environments in separate processes to circumvent the GIL')
    parser.add_argument('-m', '--mode', type=str, default='local',
                        help='One of $utils.ALLOWED_MODES (or the first letter).')
    parser.add_argument('-b', '--besteffort', default=False, action='store_true',
                        help='Whether to run in besteffort mode')
    parser.add_argument('-nc', '--nb_cores', type=int, default=8,
                        help='Number of cores to be used on the cluster')
    parser.add_argument('-w', '--wallclock', type=int, default=72,
                        help='Job wall clock time to be set on the cluster')
    parser.add_argument('-sc', '--script', default='ppo.scripts.train',
                        help='The python script to run with run_with_pytorch.sh.')
    parser.add_argument('--machines', type=str, default='f',
                        help='Which machines to use on the shared CPU cluster, ' \
                        'the choice should be in {\'s\', \'f\', \'muj\'} (slow, fast or mujuco (41)).')
    parser.add_argument('--device', type=str, default=None,
                        help='which device to run the experiments on: cuda or cpu')
    args = parser.parse_args()

    mode = utils.get_mode(args)
    seed_path, timestamp_dir = os.path.split(os.path.normpath(args.exp_path[0]))
    exp_path, _ = os.path.split(os.path.normpath(seed_path))
    exp_name = os.path.basename(exp_path)
    if mode in ('local', 'render'):
        # run the job locally
        assert len(args.exp_path) == 1
        train_args = get_train_args(seed_path, timestamp_dir, args.device)
        command = 'cd $HOME/Scripts; ./run_with_pytorch.sh {} {}'.format(
            args.script, exp_name, train_args)
        if mode == 'render':
            command += ' --render'
        os.system(command)
    else:
        p_options = utils.get_shared_machines_p_option(mode, args.machines)
        job_cluster = utils.get_job(
            mode, p_options, args.besteffort, args.nb_cores, args.wallclock)
        if len(args.exp_path) == 1:
            send_job(job_cluster, seed_path, timestamp_dir, args.device, args.script)
        else:
            for exp_path_complete in args.exp_path:
                seed_path, _ = os.path.split(os.path.normpath(exp_path_complete))
                send_job(job_cluster, seed_path, timestamp_dir, args.device, args.script)



if __name__ == '__main__':
    main()
