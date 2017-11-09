import os
import argparse
import datetime

from job.ppo import utils

TIMESTAMP = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=str,
                        help='File with argument to feed into the PPO training')
    # extra args provided in format "num_agents=8" (without two dashes)
    parser.add_argument('extra_args', type=str, nargs='*',
                        help='Additional arguments to be appended to the config arg.')
    parser.add_argument('-n', '--nb_seeds', type=int, default=1, required=False,
                        help='Number of seeds to run training with')
    parser.add_argument('-f', '--first_seed', type=int, default=1, required=False,
                        help='First seed value')
    parser.add_argument('-l', '--local', type=utils.str2bool, default=False, required=False,
                        help='Whether to run the training locally or on clear')
    parser.add_argument('-s', '--shared', type=utils.str2bool, default=False, required=False,
                        help='Whether to run the training on access1-sp')
    parser.add_argument('-e', '--edgar', type=utils.str2bool, default=False, required=False,
                        help='Whether to run the training on edgar')
    parser.add_argument('-r', '--render', type=utils.str2bool, default=False, required=False,
                        help='Whether to render the run (will run locally)')
    parser.add_argument('-b', '--besteffort', type=utils.str2bool, default=False, required=False,
                        help='Whether to run in besteffort mode')
    parser.add_argument('-nc', '--nb_cores', type=int, default=8, required=False,
                        help='Number of cores to be used on the cluster')
    parser.add_argument('-w', '--wallclock', type=int, default=72, required=False,
                        help='Job wall clock time to be set on the cluster')
    # parser.add_argument('--tf14', type=bool, default=True, required=False,
    #                     help='Whether to run the code using the updated tensorflow')
    args = parser.parse_args()

    utils.rewrite_rendered_envs_file(make_render=args.render)
    if args.shared and args.edgar:
        print('ERROR: both --edgar and --shared are True')
        return

    utils.create_parent_log_dir(args.file)
    utils.cache_code_dir(args.file, sym_link=(args.local or args.render))
    if args.local or args.render:
        utils.run_job_local(args.file, args.extra_args)
        if args.render:
            utils.rewrite_rendered_envs_file(make_render=False)
    else:
        if args.edgar:
            cluster = 'edgar'
        elif args.shared:
            cluster = 'shared'
        else:
            cluster = 'clear'
        JobPPO = utils.get_job(cluster, args.besteffort, args.nb_cores, args.wallclock)
        for seed in range(args.first_seed, args.first_seed + args.nb_seeds):
            utils.run_job_cluster(args.file, seed, args.nb_seeds, JobPPO, args.extra_args, TIMESTAMP)

if __name__ == '__main__':
    main()
