import os
import collections
from copy import deepcopy

from runtools.job.machine import JobGPU, JobCPU
from runtools.settings import ALLOWED_MODES, SCRIPTS_PATH, SCRIPT_TO_PROGRESS_WAIT_TIME, MODEL_LOG_PATH
from runtools.utils.config import read_args, append_args


def p_option(mode, machines):
    if mode == 'edgar':
        if machines == 's':
            hosts = 'cast(substring(host from \'\"\'\"\'gpuhost(.+)\'\"\'\"\') as int) BETWEEN 24 AND 27'
        elif machines == 'f':
            # hosts = 'cast(substring(host from \'\"\'\"\'gpuhost(.+)\'\"\'\"\') as int) BETWEEN 1 AND 20'
            hosts = 'cast(substring(host from \'\"\'\"\'gpuhost(.+)\'\"\'\"\') as int) BETWEEN 1 AND 9 or cast(substring(host from \'\"\'\"\'gpuhost(.+)\'\"\'\"\') as int) BETWEEN 11 AND 22'
        elif machines == 'm':
            hosts = 'cast(substring(host from \'\"\'\"\'gpuhost(.+)\'\"\'\"\') as int) BETWEEN 21 AND 22'
        elif machines == 'p':
            hosts = 'gpumodel=\'\"\'\"\'p100\'\"\'\"\''
        elif machines == 'x':
            hosts = 'gpumodel=\'\"\'\"\'titan_x\'\"\'\"\' or gpumodel=\'\"\'\"\'titan_x_pascal\'\"\'\"\''
        elif machines == 'xp':
            hosts = 'gpumodel=\'\"\'\"\'p100\'\"\'\"\' or gpumodel=\'\"\'\"\'titan_x\'\"\'\"\' or gpumodel=\'\"\'\"\'titan_x_pascal\'\"\'\"\''
        elif machines == '11':
            hosts = 'cast(substring(host from \'\"\'\"\'gpuhost(.+)\'\"\'\"\') as int) BETWEEN 11 AND 11'
        elif machines == 'e':
            hosts = 'host=\'\"\'\"\'gpuhost9\'\"\'\"\' or host=\'\"\'\"\'gpuhost11\'\"\'\"\' or host=\'\"\'\"\'gpuhost12\'\"\'\"\' or host=\'\"\'\"\'gpuhost13\'\"\'\"\' or host=\'\"\'\"\'gpuhost15\'\"\'\"\''
        if machines not in ('p', 'x', 'e'):
            hosts += ' and gpumodel!=\'\"\'\"\'gtx1080\'\"\'\"\' and gpumem>10000'
        return hosts
    # old machines can not run tensorflow >1.5 and slow
    if machines == 's':
        hosts = 'cast(substring(host from \'\"\'\"\'node(.+)-\'\"\'\"\') as int) BETWEEN 1 AND 14'
    elif machines == 'f':
        # hosts = 'cast(substring(host from \'\"\'\"\'node(.+)-\'\"\'\"\') as int) BETWEEN 21 AND 54'
        hosts = 'cast(substring(host from \'\"\'\"\'node(.+)-\'\"\'\"\') as int) BETWEEN 39 AND 54 or cast(substring(host from \'\"\'\"\'node(.+)-\'\"\'\"\') as int) BETWEEN 21 AND 37'
    else:
        raise ValueError('machines descired type {} is unknown'.format(machines))
    return ' and ({})'.format(hosts)


def job_mode(mode):
    if mode in ALLOWED_MODES:
        mode = mode
    elif mode in [m[0] for m in ALLOWED_MODES]:
        mode = [m for m in ALLOWED_MODES if m[0] == mode][0]
    else:
        raise ValueError('mode {} is not allowed, available modes: {}'.format(mode, ALLOWED_MODES))
    return mode


def cache_mode(config, on_cluster):
    # all modes:
    # cache_mode == keep -> check if cache_code dir exists. if yes, do nothing. if not, create logdir.
    # local:
    # default cache_mode is symlink: remove the cache_code dir and create a symlink
    # cluster:
    # default cache_mode is copy: remove the cache_code dir and copy the current code dir there
    if config.cache_mode is not None:
        return config.cache_mode
    if not on_cluster:
        cache_mode = 'link'
    elif on_cluster:
        cache_mode = 'copy'
    return cache_mode


def job(cluster, p_options, besteffort=False, nb_cores=8, wallclock=None):
    wallclock = 72 if wallclock is None else wallclock
    if cluster == 'edgar':
        parent_job = JobGPU
        time = '{}:0:0'.format(wallclock) if isinstance(wallclock, int) else wallclock
        l_options = ['walltime={}:0:0'.format(time)]
    elif cluster == 'access2-cp':
        parent_job = JobCPU
        time = '{}:0:0'.format(wallclock) if isinstance(wallclock, int) else wallclock
        l_options = ['nodes=1/core={},walltime={}'.format(nb_cores, time)]
    else:
        raise ValueError('unknown cluster = {}'.format(cluster))

    class JobCluster(parent_job):
        def __init__(self, run_argv, p_options):
            parent_job.__init__(self, run_argv)
            self.global_path_project = SCRIPTS_PATH
            self.local_path_exe = 'run_with_pytorch.sh'
            self.name = run_argv[0]
            self.interpreter = ''
            self.besteffort = besteffort
            self.own_p_options = [parent_job(self).own_p_options[0] + p_options]
            job_script = run_argv[1]
            if job_script in SCRIPT_TO_PROGRESS_WAIT_TIME:
                if 'scripts.augment_trajectories' not in job_script:
                    job_log_dir = os.environ['ALFRED_LOGS']
                else:
                    job_log_dir = os.environ['ALFRED_DATA']
                self.info_settings['info_path'] = os.path.join(job_log_dir, self.name, 'info.json')
                self.info_settings['max_wait_time'] = SCRIPT_TO_PROGRESS_WAIT_TIME[job_script]
        @property
        def oarsub_l_options(self):
            return parent_job(self).oarsub_l_options + l_options
    return lambda run_argv: JobCluster(run_argv, p_options)


def cluster_params(args, mode, besteffort, num_cores):
    # remove the screening character first, then parse the args
    args = args[1:]
    args = args.strip().split(' ')
    counter = 0
    while counter < len(args):
        if args[counter] == '-m':
            mode = args[counter + 1]
            mode = job_mode(mode)
            counter += 2
        elif args[counter] == '-b':
            besteffort = True
            counter += 1
        elif args[counter] == '-nc':
            num_cores = int(args[counter + 1])
            counter += 2
        else:
            raise NotImplementedError('not recognized keyword {} in consecutive_jobs arg'.format(
                args[counter]))
    return mode, besteffort, num_cores


def exp_lists(config, first_exp_id, num_exps):
    gridargs_list = get_gridargs_list(config.grid)
    if len(gridargs_list) == 1 and num_exps > 1:
        gridargs_list *= num_exps
    if config.extra_args is not None:
        assert len(config.extra_args) in (1, num_exps)
        extra_args_list = config.extra_args
    else:
        extra_args_list = [None]
    if len(extra_args_list) == 1 and num_exps > 1:
        extra_args_list *= num_exps
    exp_files = config.files
    if len(exp_files) == 1 and num_exps > 1:
        exp_files *= num_exps
    exp_names = config.exp_names
    if len(exp_names) == 1 and num_exps > 1:
        exp_names *= num_exps
    assert len(exp_files) == len(extra_args_list) and len(exp_files) == len(gridargs_list)

    first_seed = config.seed if config.seed is not None else 1
    all_seeds = range(first_seed, first_seed + config.num_seeds)

    exp_name_list, args_list, exp_meta_list = [], [], []
    for idx, (args_file, extra_args, gridargs) in enumerate(zip(exp_files, extra_args_list, gridargs_list)):
        args, exp_name, script = read_args(args_file)
        if exp_names[idx] is not None:
            exp_name = exp_names[idx]
        args = append_args(args, gridargs)
        args = append_args(args, extra_args)
        if gridargs_list[0] is not None:
            # TODO: check if this exp does not exist yet
            exp_name += '_v' + str(first_exp_id + idx)
        for seed in all_seeds:
            exp_name_cur, args_cur = deepcopy(exp_name), deepcopy(args)
            if 'train' in script:
                # TODO: what to do with other alfred scripts?
                args_cur = append_args(args_cur, ['train.seed={}'.format(seed)])
                if config.num_seeds > 1:
                    exp_name_cur += '_s{}'.format(seed)

            exp_name_list.append(exp_name_cur)
            args_list.append(args_cur)
            exp_meta_list.append(
                {'args_file': args_file,
                'extra_args': append_args(gridargs if gridargs is not None else '', extra_args),
                'script': script,
                'args': args_cur,
                'full_command': 'python3 -m {} {}'.format(script, args_cur)})
    return exp_name_list, args_list, exp_meta_list


def get_gridargs_list(grid):
    if not grid:
        return [None]
    gridargs_list = ['']
    grid_dict = collections.OrderedDict(sorted(grid.items()))
    for key, value_list in grid_dict.items():
        assert isinstance(value_list, (list, tuple))
        new_gridargs_list = []
        for gridargs_old in gridargs_list:
            for value in value_list:
                if ' ' in str(value):
                    print('removed spaces from {}, it became {}'.format(
                        value, str(value).replace(' ', '')))
                gridarg = ' {}={}'.format(key, str(value).replace(' ', ''))
                new_gridargs_list.append(gridargs_old + gridarg)
        gridargs_list = new_gridargs_list
    return gridargs_list

def append_to_lists(exp_name, new_exp_args, old_exp_meta, exp_name_list, args_list, exp_meta_list):
    new_exp_meta = deepcopy(old_exp_meta)
    new_exp_meta['args'] = new_exp_args
    new_exp_meta['full_command'] = old_exp_meta['full_command'].replace(old_exp_meta['args'], new_exp_meta['args'])
    new_exp_name = 'eval_{}'.format(exp_name)
    if 'eval.subgoals=all' in new_exp_args:
        new_exp_name += '_subgoal'
    if 'eval.select_best=True' in new_exp_args:
        new_exp_name += '_select'
    if 'eval.checkpoint=model_' in new_exp_args:
        eval_epoch = int(new_exp_args.split('eval.checkpoint=model_')[1].split('.pth')[0])
        new_exp_name += '_m{:02d}'.format(eval_epoch)
    if 'eval.fast_eval=True' in new_exp_args:
        new_exp_name += '_fast'
    if 'eval.eval_split=' in new_exp_args:
        eval_split = new_exp_args.split('eval.eval_split=')[1].split(' ')[0]
        new_exp_name += '_{}'.format(eval_split)
    exp_name_list.append(new_exp_name)
    args_list.append(new_exp_args)
    exp_meta_list.append(new_exp_meta)

def eval_exp_lists(exp_name_list_orig, args_list_orig, exp_meta_list_orig, eval_type, eval_full_range):
    if 'full' in eval_type:
        assert len(eval_full_range) in (2, 3)
        eval_epochs = list(range(*eval_full_range))

    exp_name_list, args_list, exp_meta_list = [], [], []
    for exp_name, args, exp_meta in zip(exp_name_list_orig, args_list_orig, exp_meta_list_orig):
        assert exp_meta['script'] == 'alfred.eval.eval_seq2seq'
        # assert exp_meta['script'] == 'rlons.scripts.collect'
        args = append_args(args, ['eval.exp={}'.format(exp_name)])
        if 'subgoal' in eval_type:
            args = append_args(args, ['eval.subgoals=all'])
        if '-select' in eval_type:
            args = append_args(args, ['eval.select_best=True'])
        if '-full' not in eval_type:
            append_to_lists(exp_name, args, exp_meta, exp_name_list, args_list, exp_meta_list)
        else:
            exp_name_list_l, args_list_l, exp_meta_list_l = [], [], []
            for eval_epoch in eval_epochs:
                args_epoch = append_args(
                    deepcopy(args), ['eval.fast_eval=True', 'eval.checkpoint=model_{:02d}.pth'.format(eval_epoch)])
                append_to_lists(exp_name, args_epoch, exp_meta, exp_name_list_l, args_list_l, exp_meta_list_l)
            args_select_epoch = append_args(deepcopy(args), ['eval.select_best=True'])
            append_to_lists(exp_name, args_select_epoch, exp_meta, exp_name_list, args_list, exp_meta_list)
            exp_name_list += exp_name_list_l
            args_list += args_list_l
            exp_meta_list += exp_meta_list_l
    return exp_name_list, args_list, exp_meta_list
