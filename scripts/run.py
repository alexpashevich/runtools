import argparse
import datetime
import json
import telegram_send

from scripts.utils import launch, system, parse, misc

TIMESTAMP = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')


def cache_code(exp_name_list, config, mode):
    for exp_name in exp_name_list:
        system.create_parent_log_dir(exp_name)
    if config.do_not_cache_code:
        return
    if len(exp_name_list) > 1:
        assert mode not in {'local', 'render'}
    make_sym_link = mode in {'local', 'render'} and not config.cache_code
    # make_sym_link = True
    system.cache_code_dir(
        exp_name_list[0],
        config.git_commit_ppo,
        config.git_commit_bc,
        config.git_commit_mime,
        make_sym_link)
    # cache only the first exp directory, others are sym links to it
    for exp_name in exp_name_list[1:]:
        if exp_name != exp_name_list[0]:
            system.cache_code_dir(
                exp_name, None, None, None, sym_link=True, sym_link_to_exp=exp_name_list[0])


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
                        help='One of $utils.misc.ALLOWED_MODES (or the first letter).')
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
    parser.add_argument('-gcp', '--git_commit_ppo', type=str, default=None,
                        help='Git commit to checkout the ppo repo to.')
    parser.add_argument('-gcb', '--git_commit_bc', type=str, default=None,
                        help='Git commit to checkout the bc repo to.')
    parser.add_argument('-gcm', '--git_commit_mime', type=str, default=None,
                        help='Git commit to checkout the mime repo to.')
    parser.add_argument('--machines', type=str, default='f',
                        help='Which machines to use on the shared CPU cluster, ' \
                        'the choice should be in {\'s\', \'f\', \'muj\'} (slow, fast or mujuco (41)).')
    parser.add_argument('-sc', '--script', default='ppo.scripts.train',
                        help='The python script to run with run_with_pytorch.sh.')
    # TODO: fix, it's redundant
    parser.add_argument('-dcc', '--do_not_cache_code', default=False, action='store_true',
                        help='If the code caching should be disabled.')
    parser.add_argument('-cc', '--cache_code', default=False, action='store_true',
                        help='If the code caching should be enabled in local mode.')
    parser.add_argument('-fi', '--first_exp_id', type=int, default=1,
                        help='First experiment name id.')
    # Google Cloud Engine settings
    parser.add_argument('-i', '--gce_id', type=int, default=None,
                        help='Google Compute Engine id in $GINSTS (starting from 1).')
    parser.add_argument('-ng', '--num_gce', type=int, default=1,
                        help='Number of GCE to distribute the experiments.')
    return parser.parse_args()


def main():
    config = parse_config()
    mode = misc.get_mode(config)
    num_exps = max(len(config.files),
                   1 if config.exp_names is None else len(config.exp_names),
                   1 if config.extra_args is None else len(config.extra_args))
    if config.grid:
        num_exps *= len(config.grid)
    exp_name_list, args_list, exp_meta_list = parse.get_exp_lists(config, config.first_exp_id, num_exps)
    if config.exp_names:
        if len(config.exp_names) == len(exp_name_list):
            exp_name_list = config.exp_names
        elif len(config.exp_names) == 1:
            exp_name_list = config.exp_names * num_exps
        else:
            raise RuntimeError('exp names size is neither 1, nor $NUM_EXPS: {}'.format(
                config.exp_names))

    cache_code(exp_name_list, config, mode)

    # run the experiment(s)
    for exp_id, (exp_name, args, exp_meta) in enumerate(zip(exp_name_list, args_list, exp_meta_list)):
        script = exp_meta['script'] if exp_meta['script'] is not None else config.script
        if mode in ('local', 'render'):
            # run locally
            assert len(exp_name_list) == 1
            render = (mode == 'render')
            # TODO: add an option to enforce message sending in the local mode
            # send_report_message(exp_name, exp_meta, [config.seed], mode)
            launch.job_local(
                exp_name, args, script, config.files[0], seed=config.seed, render=render)
        elif mode != 'gce':
            # run on INRIA cluster
            p_options = misc.get_shared_machines_p_option(mode, config.machines)
            JobPPO = misc.get_job(
                mode, p_options, config.besteffort, config.num_cores, config.wallclock)
            first_seed = config.seed if config.seed is not None else 1
            all_seeds = range(first_seed, first_seed + config.num_seeds)
            for seed in all_seeds:
                launch.job_cluster(
                    exp_name, args, script, exp_meta['args_file'], seed, config.num_seeds,
                    JobPPO, TIMESTAMP)
            send_report_message(exp_name, exp_meta, list(all_seeds), mode)
        else:
            # run on GCE
            raise NotImplementedError('need to implement the new scripts supporting')
            first_seed = config.seed if config.seed is not None else 1
            all_seeds = range(first_seed, first_seed + config.num_seeds)
            for seed in all_seeds:
                exp_number = seed - first_seed + exp_id * config.num_seeds
                exp_total = len(exp_name_list) * config.num_seeds
                # If more than a single node to submit, change gce_id
                gce_id = int(config.gce_id + exp_number // (exp_total / config.num_gce))
                launch.job_gce(exp_name, args, seed, config.num_seeds, TIMESTAMP, gce_id)
                send_report_message(exp_name, exp_meta, [seed], mode + '-' + str(gce_id))


if __name__ == '__main__':
    main()
