import argparse
import datetime
import json
import collections
import os

from job.ppo import utils

TIMESTAMP = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('files', type=str, nargs='*',
                        help='List of files with argument to feed into the PPO training')
    # extra args provided in format "num_agents=8" (without two dashes)
    parser.add_argument('--extra_args', type=json.loads, default=[],
                        help='Additional arguments to be appended to the config args')
    parser.add_argument('-n', '--nb_seeds', type=int, default=1,
                        help='Number of seeds to run training with')
    parser.add_argument('-f', '--first_seed', type=int, default=1,
                        help='First seed value')
    parser.add_argument('-s', '--seed', type=int, default=None,
                        help='Seed to use (in a local experiment).')
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
    parser.add_argument('-m', '--machines', type=str, default='f',
                        help='Which machines to use on the shared CPU cluster, ' \
                        'the choice should be in {\'s\', \'f\'} (slow or fast).')
    parser.add_argument('--tf15', default=True, action='store_false',
                        help='Whether to use tensorflow 1.5')
    parser.add_argument('-fte', '--fine_tune_exp', type=str, default=None,
                        help='Name of the experiment to use for the finetuning (if not None).')
    parser.add_argument('-ftt', '--fine_tune_ts', type=str, default=None,
                        help='Timestep of the experiment to use for the finetuning (if not None).')
    # TODO: delete later
    parser.add_argument('--mlsh', default=False, action='store_true',
                        help='Whether to run MLSH code.')
    args = parser.parse_args()

    if not args.mlsh:
        utils.rewrite_rendered_envs_file(make_render=args.render)
        extra_args_str = utils.stringify_extra_args(sorted(args.extra_args))

        # cache the code and create directories
        if args.grid is not None:
            grid_dict_sorted = collections.OrderedDict(sorted(args.grid.items()))
            assert not args.local and not args.render
            gridargs_list = utils.gridargs_list(grid_dict_sorted)
            for filename in args.files:
                for gridargs in gridargs_list:
                    other_args = gridargs + extra_args_str if extra_args_str is not None else gridargs
                    utils.create_parent_log_dir(filename, other_args)
                    utils.cache_code_dir(filename, args.git_commit_agents, args.git_commit_grasp_env,
                                        other_args,
                                        sym_link=(args.local or args.render))
        else:
            gridargs_list = None
            for filename in args.files:
                utils.create_parent_log_dir(filename, extra_args_str)
                utils.cache_code_dir(filename, args.git_commit_agents, args.git_commit_grasp_env,
                                    extra_args_str, sym_link=(args.local or args.render))
    else:
        extra_args_str = None
        gridargs_list = None

    # fine_tune checkpoint
    if args.fine_tune_exp and args.fine_tune_ts:
        ckpt_file = os.path.join('/home/thoth/apashevi/Logs/agents/', args.fine_tune_exp,
                                 'seed{}', args.fine_tune_ts, 'checkpoint')
        # fine_tune_args = ' --checkpoint_fc={}'.format(
        #     os.path.join('/home/thoth/apashevi/Logs/agents/', args.fine_tune_exp,
        #                  'seed{}', args.fine_tune_ts, 'checkpoint'))
    else:
        ckpt_file = None

    # run the experiment(s)
    if args.local or args.render:
        assert len(args.files) == 1
        assert not args.mlsh
        if ckpt_file:
            # TODO: fix seed
            with open(ckpt_file.format(1)) as cf:
                not_in_name_args = ' --checkpoint_fc={}'.format(cf.readline().split('"')[1])
        else:
            not_in_name_args = None
        utils.run_job_local(
            args.files[0], extra_args_str, seed=args.seed, not_in_name_args=not_in_name_args)
        if args.render:
            utils.rewrite_rendered_envs_file(make_render=False)
    else:
        cluster = 'edgar' if args.edgar else 'access1-cp'
        if not args.edgar and args.machines:
            p_options = utils.get_shared_machines_p_option(args.machines)
        else:
            p_options = ''
        # old machines can not run tensorflow >1.5
        use_tf15 = True if args.machines == 's' or args.tf15 else False
        JobPPO = utils.get_job(
            cluster, p_options, args.besteffort, args.nb_cores, args.wallclock, use_tf15, args.mlsh)

        for filename in args.files:
            if gridargs_list is not None:
                for gridargs in gridargs_list:
                    other_args = gridargs + extra_args_str if extra_args_str is not None else gridargs
                    for seed in range(args.first_seed, args.first_seed + args.nb_seeds):
                        if ckpt_file:
                            with open(ckpt_file.format(seed)) as cf:
                                not_in_name_args = ' --checkpoint_fc={}'.format(
                                    cf.readline().split('"')[1])
                        else:
                            not_in_name_args = None
                        utils.run_job_cluster(
                            filename, seed, args.nb_seeds, JobPPO, TIMESTAMP, other_args, not_in_name_args)
            else:
                for seed in range(args.first_seed, args.first_seed + args.nb_seeds):
                    if ckpt_file:
                        with open(ckpt_file.format(seed)) as cf:
                            not_in_name_args = ' --checkpoint_fc={}'.format(
                                cf.readline().split('"')[1])
                    else:
                        not_in_name_args = None
                    utils.run_job_cluster(filename, seed, args.nb_seeds, JobPPO,
                                          TIMESTAMP, extra_args_str, not_in_name_args)

if __name__ == '__main__':
    main()
