import argparse
import json
import os
import telegram_send

from runtools.utils import jobs, system, get


def send_report_message(exp_name, exp_meta, seeds, mode):
    report_message = 'launched job `{0}` (seeds %s) on %s\n```details = {1}```'.format(
        exp_name, exp_meta)
    report_message = report_message % (seeds, mode)
    try:
        telegram_send.send([report_message])
    except:
        # probably I am running a local job from a cluster node
        pass


def parse_config():
    parser = argparse.ArgumentParser()
    parser.add_argument('files', type=str, nargs='*',
                        help='List of files with argument to feed into the training script.')
    # extra args provided in the normal format: "--num_agents=8" or "agents.num=8"
    parser.add_argument('-e', '--extra_args', type=str, default=None, nargs='+',
                        help='Additional arguments to be appended to the config args.')
    parser.add_argument('-en', '--exp_names', default=None, nargs='+',
                        help='Exp name(s) in case if the filename is not good.')
    parser.add_argument('-n', '--num_seeds', type=int, default=1,
                        help='Number of seeds to run training with.')
    parser.add_argument('-s', '--seed', type=int, default=None,
                        help='Seed to use.')
    parser.add_argument('-m', '--mode', type=str, default='local',
                        help='One of $settings.ALLOWED_MODES (or the first letter).')
    parser.add_argument('-b', '--besteffort', default=False, action='store_true',
                        help='Whether to run in besteffort mode')
    parser.add_argument('-nc', '--num_cores', type=int, default=8,
                        help='Number of cores to be used on the cluster.')
    parser.add_argument('-w', '--wallclock', type=int, default=None,
                        help='Job wallclock time to be set on the cluster.')
    parser.add_argument('-g', '--grid', type=json.loads, default=None,
                        help='Dictionary with grid of hyperparameters to run experiments with. ' \
                        'It should be a dictionary with key equal to the argument you want to ' \
                        'gridsearch on and value equal to list of values you want it to be.')
    parser.add_argument('-gcr', '--git_commit_rlons', type=str, default=None,
                        help='Git commit to checkout the RLonS repo to.')
    parser.add_argument('-gcm', '--git_commit_mime', type=str, default=None,
                        help='Git commit to checkout the mime repo to.')
    parser.add_argument('--machines', type=str, default='f',
                        help='Which machines to use on the shared CPU cluster, ' \
                        'the choice should be in {"s", "f"} (slow or fast).')
    parser.add_argument('-sc', '--script', default='rlons.scripts.train',
                        help='The python script to run with run_with_pytorch.sh.')
    parser.add_argument('-cm', '--cache_mode', default=None,
                        help='Cache mode, should be in {"keep", "symlink", "copy"}')
    parser.add_argument('-fi', '--first_exp_id', type=int, default=1,
                        help='First experiment name id.')
    # evaluation (deprecated)
    parser.add_argument('-ei', '--evaluation_interval', type=json.loads, default=None,
                        help='[first_epoch, last_epoch, iter_epoch]')
    parser.add_argument('-es', '--evaluation_seeds', type=json.loads, default=None,
                        help='List of seeds to evaluate.')
    parser.add_argument('-ed', '--evaluation_dir', type=str, default=None,
                        help='Path to the eval dirs with %d instead of the seed number')
    return parser.parse_args()


def main():
    config = parse_config()
    mode = get.mode(config)
    num_exps = max(len(config.files),
                   1 if config.exp_names is None else len(config.exp_names),
                   1 if config.extra_args is None else len(config.extra_args))
    if config.grid:
        num_exps *= len(config.grid)
    exp_name_list, args_list, exp_meta_list = get.exp_lists(config, config.first_exp_id, num_exps)

    if config.exp_names:
        if len(config.exp_names) == len(exp_name_list):
            exp_name_list = config.exp_names
        elif len(config.exp_names) == 1:
            exp_name_list = config.exp_names * num_exps
        else:
            raise RuntimeError('exp names size is neither 1, nor $NUM_EXPS: {}'.format(
                config.exp_names))

    if config.evaluation_seeds is not None:
        assert config.evaluation_interval is not None
        assert config.evaluation_dir is not None
        assert len(config.evaluation_interval) == 3
        exp_name_list, args_list, exp_meta_list = get.eval_exp_lists(
            exp_name_list, args_list, exp_meta_list,
            config.evaluation_interval, config.evaluation_seeds, config.evaluation_dir)

    if len(exp_name_list) > 1:
        assert mode not in {'local', 'render'}
    system.create_cache_dir(
        exp_name_list, get.cache_mode(config, mode), config.git_commit_rlons, config.git_commit_mime)

    # run the experiment(s)
    for exp_id, (exp_name, args, exp_meta) in enumerate(zip(exp_name_list, args_list, exp_meta_list)):
        script = exp_meta['script'] if exp_meta['script'] is not None else config.script
        if mode in ('local', 'render'):
            # run locally
            assert len(exp_name_list) == 1
            render = (mode == 'render')
            # TODO: add an option to enforce message sending in the local mode
            # send_report_message(exp_name, exp_meta, [config.seed], mode)
            system.change_sys_path(system.get_sys_path_clean(), exp_name)
            jobs.run_local(
                exp_name, args, script, config.files[0], seed=config.seed, render=render)
        else:
            # run on INRIA cluster
            p_options = get.p_option(mode, config.machines)
            JobCluster = get.job(
                mode, p_options, config.besteffort, config.num_cores, config.wallclock)
            first_seed = config.seed if config.seed is not None else 1
            all_seeds = range(first_seed, first_seed + config.num_seeds)
            for seed in all_seeds:
                jobs.run_cluster(
                    exp_name, args, script, exp_meta['args_file'], seed, config.num_seeds, JobCluster)
            send_report_message(exp_name, exp_meta, list(all_seeds), mode)


if __name__ == '__main__':
    main()
