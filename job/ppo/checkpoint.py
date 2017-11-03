from job.ppo import utils
import os
import argparse
import tensorflow as tf

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('exp_path', type=str,
                        help='Full experiment path (to the dir where the config is stored)')
    parser.add_argument('-e', '--env_process', type=utils.str2bool, default=True, required=False,
                        help='Step environments in separate processes to circumvent the GIL')
    parser.add_argument('-r', '--render', type=utils.str2bool, default=True, required=False,
                        help='Whether to render the run')
    args = parser.parse_args()

    sys_path_clean = utils.get_sys_path_clean()
    seed_path, _ = os.path.split(os.path.normpath(args.exp_path))
    exp_path, _ = os.path.split(os.path.normpath(seed_path))
    utils.change_sys_path(sys_path_clean, exp_path)
    import agents.scripts.train as trainer
    from agents.scripts import utility
    config = utility.load_config(args.exp_path)
    with config.unlocked:
        config.num_agents = 8

    import pudb; pudb.set_trace()
    exp_name = os.path.basename(exp_path)
    rendered_envs_path = '/home/thoth/apashevi/scratch_remote/Cache/Code/{}/rlgrasp/rendered_envs.py'.format(exp_name)
    utils.rewrite_rendered_envs_file(args.render, rendered_envs_path)
    for score in trainer.train(config, args.env_process):
        tf.logging.info('Score {}'.format(score))

    if args.render:
        utils.rewrite_rendered_envs_file(False, rendered_envs_path)

if __name__ == '__main__':
    main()
