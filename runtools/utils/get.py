import collections
from copy import deepcopy

from runtools.job.machine import JobGPU, JobCPU
from runtools.settings import ALLOWED_MODES, SCRIPTS_PATH
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
        return hosts + ' and gpumem > 10000'
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
            self.job_name = run_argv[0]
            self.interpreter = ''
            self.besteffort = besteffort
            self.own_p_options = [parent_job(self).own_p_options[0] + p_options]
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
        exp_name_list.append(exp_name)
        args_list.append(args)
        exp_meta_list.append(
            {'args_file': args_file,
             'extra_args': append_args(gridargs if gridargs is not None else '', extra_args),
             'script': script,
             'args': args,
             'full_command': 'python3 -m {} {}'.format(script, args)})
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


def eval_exp_lists(exp_name_list, args_list, exp_meta_list, eval_interval, eval_seeds, eval_dir):
    # deprecated, maybe delete later
    eval_first_epoch, eval_last_epoch, eval_iter = eval_interval
    exp_name_list_new, args_list_new, exp_meta_list_new = [], [], []
    for exp_name, args, exp_meta in zip(exp_name_list, args_list, exp_meta_list):
        assert exp_meta['script'] == 'rlons.scripts.collect'
        # assert exp_meta['script'] == 'rlons.scripts.collect_demos'
        for eval_seed in eval_seeds:
            exp_name_seed = '{}_seed{}'.format(exp_name, eval_seed)
            args_seed = append_args(
                args, ['model.dir={}'.format(eval_dir.strip() % eval_seed)])
            for eval_epoch in range(eval_first_epoch, eval_last_epoch, eval_iter):
                args_seed_epoch = append_args(
                    args_seed, ['collect.first_epoch={}'.format(eval_epoch),
                                'collect.last_epoch={}'.format(eval_epoch + eval_iter)])
                exp_meta_seed_epoch = deepcopy(exp_meta)
                exp_meta_seed_epoch['args'] = args_seed_epoch
                exp_name_list_new.append(exp_name_seed)
                args_list_new.append(args_seed_epoch)
                exp_meta_list_new.append(exp_meta_seed_epoch)

    return exp_name_list_new, args_list_new, exp_meta_list_new

