import os
import argparse

import tensorflow as tf

from job.ppo import utils
from job.job_manager import manage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('exp_path', type=str,
                        help='Full experiment path (to the dir where the config is stored)')
    parser.add_argument('-nep', '--no_env_process', default=False, action='store_true',
                        help='Step environments in separate processes to circumvent the GIL')
    parser.add_argument('-r', '--render', default=False, action='store_true',
                        help='Whether to render the run')
    parser.add_argument('-c', '--cpu', default=False, action='store_true',
                        help='Whether to run the training on access1-cp')
    parser.add_argument('-e', '--edgar', default=False, action='store_true',
                        help='Whether to run the training on edgar')
    parser.add_argument('-b', '--besteffort', default=False, action='store_true',
                        help='Whether to run in besteffort mode')
    parser.add_argument('-nc', '--nb_cores', type=int, default=8, required=False,
                        help='Number of cores to be used on the cluster')
    parser.add_argument('-w', '--wallclock', type=int, default=72, required=False,
                        help='Job wall clock time to be set on the cluster')
    args = parser.parse_args()

    sys_path_clean = utils.get_sys_path_clean()
    seed_path, timestamp_dir = os.path.split(os.path.normpath(args.exp_path))
    exp_path, seed_dir = os.path.split(os.path.normpath(seed_path))
    exp_name = os.path.basename(exp_path)
    rendered_envs_path = '/home/thoth/apashevi/scratch_remote/Cache/Code/{}/rlgrasp/rendered_envs.py'.format(exp_name)
    if not args.cpu and not args.edgar:
        # run the job locally
        utils.change_sys_path(sys_path_clean, exp_path)
        import agents.scripts.train as trainer
        from agents.scripts import utility
        config = utility.load_config(args.exp_path)
        with config.unlocked:
            config.num_agents = 4

        utils.rewrite_rendered_envs_file(args.render, rendered_envs_path)
        for score in trainer.train(config, not args.no_env_process):
            tf.logging.info('Score {}'.format(score))

        if args.render:
            utils.rewrite_rendered_envs_file(False, rendered_envs_path)
    else:
        if args.edgar:
            cluster = 'edgar'
        else:
            cluster = 'access1-cp'
        utils.rewrite_rendered_envs_file(False, rendered_envs_path)
        JobPPO = utils.get_job(cluster, args.besteffort, args.nb_cores, args.wallclock)
        timestamp = timestamp_dir.split('-')[0]
        config =  timestamp_dir.split('-')[1]
        args = '--logdir={} --timestamp={} --config={}'.format(seed_path, timestamp, config)
        exp_name_seed = '{}-s{}'.format(exp_name, seed_dir.replace('seed', ''))
        manage([JobPPO([exp_name_seed, args])], only_initialization=False, sleep_duration=1)

if __name__ == '__main__':
    main()
