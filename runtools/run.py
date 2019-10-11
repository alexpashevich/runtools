import argparse
import json

from runtools.utils import jobs, system, get


def parse_config():
    parser = argparse.ArgumentParser()
    # which jobs to run
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
    parser.add_argument('-fi', '--first_exp_id', type=int, default=1,
                        help='First experiment name id.')
    parser.add_argument('-sc', '--script', default='rlons.train',
                        help='The python script to run with run_with_pytorch.sh.')
    parser.add_argument('-g', '--grid', type=json.loads, default=None,
                        help='Dictionary with grid of hyperparameters to run experiments with. ' \
                        'It should be a dictionary with key equal to the argument you want to ' \
                        'gridsearch on and value equal to list of values you want it to be.')
    # what to do with the code
    parser.add_argument('-cm', '--cache_mode', default=None,
                        help='Cache mode, should be in {"keep", "link", "copy"}')
    parser.add_argument('-gcr', '--git_commit_rlons', type=str, default=None,
                        help='Git commit to checkout the RLonS repo to.')
    parser.add_argument('-gcm', '--git_commit_mime', type=str, default=None,
                        help='Git commit to checkout the mime repo to.')
    # where to run them
    parser.add_argument('-m', '--mode', type=str, default='local',
                        help='One of $settings.ALLOWED_MODES (or the first letter).')
    parser.add_argument('--machines', type=str, default='f',
                        help='Which machines to use on the shared CPU cluster, ' \
                        'the choice should be in {"s", "f"} (slow or fast).')
    parser.add_argument('-b', '--besteffort', default=False, action='store_true',
                        help='Whether to run in besteffort mode')
    parser.add_argument('-nc', '--num_cores', type=int, default=8,
                        help='Number of cores to be used on the cluster.')
    parser.add_argument('-w', '--wallclock', type=int, default=None,
                        help='Job wallclock time to be set on the cluster.')
    # evaluation stuff (deprecated)
    parser.add_argument('-ei', '--evaluation_interval', type=json.loads, default=None,
                        help='[first_epoch, last_epoch, iter_epoch]')
    parser.add_argument('-es', '--evaluation_seeds', type=json.loads, default=None,
                        help='List of seeds to evaluate.')
    parser.add_argument('-ed', '--evaluation_dir', type=str, default=None,
                        help='Path to the eval dirs with %d instead of the seed number')
    # consequtive runs
    parser.add_argument('-cj', '--consecutive_jobs', type=str, default=None, nargs='+',
                        help='Path to the eval dirs with %d instead of the seed number')
    # the CJ args are passed in the normal format
    # but we need to screen them with a random characters so that argparse does not try to read them
    # an example: -cj '# -m a -b' '$ -m a -nc 32'
    return parser.parse_args()


def main():
    config = parse_config()
    mode = get.job_mode(config.mode)
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
        assert mode not in {'local', 'render'} or config.consecutive_jobs
    if config.consecutive_jobs:
        assert len(config.consecutive_jobs) == len(exp_name_list)

    cache_mode = get.cache_mode(
        config, on_cluster=(mode in ('edgar', 'access2-cp') or config.consecutive_jobs))
    system.create_cache_dir(
        exp_name_list, cache_mode, config.git_commit_rlons, config.git_commit_mime)

    # run the experiment(s)
    jobs_list = []
    for exp_id, (exp_name, args, exp_meta) in enumerate(zip(exp_name_list, args_list, exp_meta_list)):
        script = exp_meta['script'] if exp_meta['script'] is not None else config.script
        job_mode, job_besteffort, job_num_cores = mode, config.besteffort, config.num_cores
        if config.consecutive_jobs:
            job_mode, job_besteffort, job_num_cores = get.cluster_params(
                config.consecutive_jobs[exp_id], mode, config.besteffort, config.num_cores)
        if job_mode in ('local', 'render'):
            # run locally
            assert len(exp_name_list) == 1
            render = (job_mode == 'render')
            # TODO: add an option to enforce message sending in the local mode
            # send_report_message(exp_name, exp_meta, [config.seed], mode)
            system.change_sys_path(system.get_sys_path_clean(), exp_name)
            jobs.run_locally(
                exp_name, args, script, config.files[0], seed=config.seed, render=render)
        else:
            # prepare a job to run on INRIA cluster
            p_options = get.p_option(job_mode, config.machines)
            JobCluster = get.job(job_mode, p_options, job_besteffort, job_num_cores, config.wallclock)
            first_seed = config.seed if config.seed is not None else 1
            all_seeds = range(first_seed, first_seed + config.num_seeds)
            for seed in all_seeds:
                jobs_list.append(jobs.init_on_cluster(
                    exp_name, args, script, exp_meta['args_file'], seed, config.num_seeds, JobCluster))
    jobs.run_on_cluster(config, jobs_list, exp_name_list, exp_meta_list)


if __name__ == '__main__':
    main()
