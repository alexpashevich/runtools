import argparse
import datetime
import json

from job.ppo import utils

TIMESTAMP = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=str,
                        help='File with argument to feed into the PPO training')
    # extra args provided in format "num_agents=8" (without two dashes)
    parser.add_argument('extra_args', type=str, nargs='*',
                        help='Additional arguments to be appended to the config args')
    parser.add_argument('-n', '--nb_seeds', type=int, default=1,
                        help='Number of seeds to run training with')
    parser.add_argument('-f', '--first_seed', type=int, default=1,
                        help='First seed value')
    parser.add_argument('-l', '--local', default=False, action='store_true',
                        help='Whether to run the training locally or on clear')
    parser.add_argument('-e', '--edgar', default=False, action='store_true',
                        help='Whether to run the training on edgar')
    parser.add_argument('-r', '--render', default=False, action='store_true',
                        help='Whether to render the run (will run locally)')
    parser.add_argument('-b', '--besteffort', default=False, action='store_true',
                        help='Whether to run in besteffort mode')
    parser.add_argument('-nc', '--nb_cores', type=int, default=8,
                        help='Number of cores to be used on the cluster')
    parser.add_argument('-w', '--wallclock', type=int, default=None,
                        help='Job wallclock time to be set on the cluster')
    parser.add_argument('-g', '--grid', type=json.loads, default=None,
                        help='Dictionary with grid of hyperparameters to run experiments with. ' \
                        'It should be a dictionary with key equal to the argument you want to ' \
                        'gridsearch on and value equal to list of values you want it to be.')
    parser.add_argument('-gca', '--git_commit_agents', type=str, default=None,
                        help='Git commit to checkout the agents repo to')
    parser.add_argument('-gcg', '--git_commit_grasp_env', type=str, default=None,
                        help='Git commit to checkout the grasp_env repo to')
    args = parser.parse_args()

    utils.rewrite_rendered_envs_file(make_render=args.render)

    if args.grid is not None:
        assert not args.local and not args.render
        gridargs_list = utils.gridargs_list(args.grid)
        for gridargs in gridargs_list:
            utils.create_parent_log_dir(args.file, gridargs)
            utils.cache_code_dir(args.file, args.git_commit_agents, args.git_commit_grasp_env,
                                 gridargs,
                                 sym_link=(args.local or args.render))
    else:
        gridargs_list = None
        utils.create_parent_log_dir(args.file)
        utils.cache_code_dir(args.file, args.git_commit_agents, args.git_commit_grasp_env,
                             sym_link=(args.local or args.render))

    if args.local or args.render:
        utils.run_job_local(args.file, args.extra_args)
        if args.render:
            utils.rewrite_rendered_envs_file(make_render=False)
    else:
        cluster = 'edgar' if args.edgar else 'access1-cp'
        JobPPO = utils.get_job(cluster, args.besteffort, args.nb_cores, args.wallclock)
        if gridargs_list is not None:
            for gridargs in gridargs_list:
                for seed in range(args.first_seed, args.first_seed + args.nb_seeds):
                    utils.run_job_cluster(args.file, seed, args.nb_seeds, JobPPO,
                                          args.extra_args, TIMESTAMP, gridargs)
        else:
            for seed in range(args.first_seed, args.first_seed + args.nb_seeds):
                utils.run_job_cluster(args.file, seed, args.nb_seeds, JobPPO,
                                      args.extra_args, TIMESTAMP)

if __name__ == '__main__':
    main()
