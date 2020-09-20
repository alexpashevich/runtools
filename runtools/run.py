import argparse
import json
import time
import numpy as np

from runtools.utils import jobs, system, get


def parse_config():
    parser = argparse.ArgumentParser()
    # which jobs to run
    parser.add_argument('files', type=str, nargs='*',
                        help='List of files with argument to feed into the training script.')
    # extra args provided in the normal format: "--num_agents=8" or "agents.num=8"
    parser.add_argument('-e', '--extra_args', type=str, default=None, nargs='+',
                        help='Additional arguments to be appended to the config args.')
    parser.add_argument('-en', '--exp_names', default=[None], nargs='+',
                        help='Exp name(s) in case if the filename is not good.')
    parser.add_argument('-n', '--num_seeds', type=int, default=1,
                        help='Number of seeds to run training with.')
    parser.add_argument('-s', '--seed', type=int, default=None,
                        help='Seed to use.')
    parser.add_argument('-fi', '--first_exp_id', type=int, default=1,
                        help='First experiment name id.')
    parser.add_argument('-sc', '--script', default='alfred.train.train_seq2seq',
                        help='The python script to run with run_with_pytorch.sh.')
    parser.add_argument('-g', '--grid', type=json.loads, default=None,
                        help='Dictionary with grid of hyperparameters to run experiments with. ' \
                        'It should be a dictionary with key equal to the argument you want to ' \
                        'gridsearch on and value equal to list of values you want it to be.')
    # what to do with the code
    parser.add_argument('-cm', '--cache_mode', default=None,
                        help='Cache mode, should be in {"keep", "link", "copy"}')
    parser.add_argument('-sym', '--sym_link_to_exp', default=None,
                        help='Sym link the code to the one of the specified experiment (must be a valid one)')
    parser.add_argument('-gca', '--git_commit_alfred', type=str, default=None,
                        help='Git commit to checkout the ALFRED repo to.')
    # where to run them
    parser.add_argument('-m', '--mode', type=str, default='local',
                        help='One of $settings.ALLOWED_MODES (or the first letter).')
    parser.add_argument('-ma', '--machines', type=str, default='f',
                        help='Which machines to use on the clusters, ' \
                        'the choice should be in {"s", "f"} (slow/gpu24-27 or fast/gpu1-22).')
    parser.add_argument('-di', '--cuda_devices', type=str, default=None,
                        help='Which GPU(s) to use.')
    parser.add_argument('-b', '--besteffort', default=False, action='store_true',
                        help='Whether to run in besteffort mode')
    parser.add_argument('-nc', '--num_cores', type=int, default=8,
                        help='Number of cores to be used on the cluster.')
    parser.add_argument('-w', '--wallclock', type=int, default=None,
                        help='Job wallclock time to be set on the cluster.')
    # evaluation stuff (new)
    parser.add_argument('-et', '--eval_type', type=str, default=None,
                        choices=('task', 'subgoal', 'task-full', 'subgoal-full', 'task-select', 'subgoal-select', 'task-find', 'subgoal-find'),
                        help='Type of alfred evaluation')
    parser.add_argument('-er', '--eval_full_range', type=int, nargs='+', default=[3, 20, 2],
                        help='first_epoch, last_epoch, (iter_epoch)')
    # misc
    parser.add_argument('-cj', '--consecutive_jobs', type=str, default=None, nargs='+',
                        help='Path to the eval dirs with %d instead of the seed number')
    # the CJ args are passed in the normal format
    # but we need to screen them with a random characters so that argparse does not try to read them
    # an example: -cj '# -m a -b' '$ -m a -nc 32'
    parser.add_argument('-d', '--debug', default=False, action='store_true',
                        help='Whether to run the code in the main thread (debug mode)')
    parser.add_argument('-sl', '--sleep', type=int, default=None,
                        help='Whether to sleep before running the code')
    return parser.parse_args()


def main():
    config = parse_config()
    if config.sleep:
        print('Will sleep {} seconds'.format(config.sleep))
        time.sleep(config.sleep)

    mode = get.job_mode(config.mode)
    num_exps = max(len(config.files),
                   1 if config.exp_names is None else len(config.exp_names),
                   1 if config.extra_args is None else len(config.extra_args))
    if config.grid:
        assert isinstance(config.grid, dict)
        num_exps *= np.prod([len(l) for l in config.grid.values()])
    exp_name_list, args_list, exp_meta_list = get.exp_lists(config, config.first_exp_id, num_exps)

    if config.eval_type is not None:
        # the user is asking for evaluation
        if mode == 'edgar':
            assert config.machines in ('f', 'e') # f is default, e is evaluation nodes
            config.machines = 'e'
        exp_name_list, args_list, exp_meta_list = get.eval_exp_lists(
            exp_name_list, args_list, exp_meta_list, config.eval_type, config.eval_full_range)

    # if len(exp_name_list) > 1:
    #     # on a local machine only a single job should be executed or several consecutive ones
    #     assert mode not in {'local', 'render'} or config.consecutive_jobs
    if config.consecutive_jobs:
        # while launching consecutive jobs, we should provide parameters for all exps
        assert len(config.consecutive_jobs) == len(exp_name_list)

    cache_mode = get.cache_mode(config, on_cluster=(mode in ('edgar', 'access2-cp') or config.consecutive_jobs))
    system.create_cache_dir(exp_name_list, cache_mode, config.git_commit_alfred, config.sym_link_to_exp)

    # to make sure that eval-select is launched after all eval-fasts
    if mode in ('local', 'render') and config.eval_type is not None:
        exp_name_list, args_list, exp_meta_lsit = reversed(exp_name_list), reversed(args_list), reversed(exp_meta_list)
        # exp_name_list = list(exp_name_list)[:-1]
        # args_list = list(args_list)[:-1]
        # exp_meta_list = list(exp_meta_list)[:-1]

    # run the experiment(s)
    jobs_list = []
    # if config.cuda_devices is None and mode == 'gcp':
    #     import torch
    #     config.cuda_devices = list(range(0, torch.cuda.device_count()))
    for exp_id, (exp_name, args, exp_meta) in enumerate(zip(exp_name_list, args_list, exp_meta_list)):
        script = exp_meta['script'] if exp_meta['script'] is not None else config.script
        job_mode, job_besteffort, job_num_cores = mode, config.besteffort, config.num_cores
        if config.consecutive_jobs:
            # get cluster parameters of the current job
            job_mode, job_besteffort, job_num_cores = get.cluster_params(
                config.consecutive_jobs[exp_id], mode, config.besteffort, config.num_cores)
        if job_mode in ('local', 'render'):
            # run locally
            # assert len(exp_name_list) == 1
            render = (job_mode == 'render')
            # TODO: add an option to enforce message sending in the local mode
            # send_report_message(exp_name, exp_meta, [config.seed], mode)
            # cuda_device = config.cuda_devices[0] if isinstance(config.cuda_devices, list) else None
            jobs.run_locally(
                exp_name, args, script, config.files[0], config.seed,
                render, config.debug, config.cuda_devices)
        # elif job_mode == 'gcp':
        #     assert isinstance(config.cuda_devices, list)
        #     cuda_device = config.cuda_devices[exp_id % len(exp_name_list)]
        #     jobs.run_locally(
        #         exp_name, args, script, config.files[0], config.seed,
        #         False, config.debug, cuda_device, run_async=True)

        else:
            # prepare a job to run on INRIA cluster
            p_options = get.p_option(job_mode, config.machines)
            JobCluster = get.job(job_mode, p_options, job_besteffort, job_num_cores, config.wallclock)
            jobs_list.append(jobs.init_on_cluster(exp_name, args, script, exp_meta['args_file'], JobCluster))
    jobs.run_on_cluster(config, jobs_list, exp_name_list, exp_meta_list)


if __name__ == '__main__':
    main()
