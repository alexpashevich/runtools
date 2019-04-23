import os
import json
import collections


def read_args(args_file):
    exp_name = os.path.basename(args_file).split('.')[0]
    with open(args_file) as f:
        args_lines = f.read().splitlines()
    if args_lines[0][:2] == '#!':
        script = args_lines[0][2:]
        args_lines = args_lines[1:]
    else:
        script = None

    good_args_lines = []
    for line in args_lines:
        if line.replace('\t', '').replace('\n', '').replace(' ', '')[0] != '#':
            good_args_lines.append(line)

    if args_file.endswith('.json'):
        args = read_json(good_args_lines)
    else:
        args = read_text(good_args_lines)
    return args, exp_name, script


def read_text(args_lines):
    args = ''
    for line in args_lines:
        for char in {' ', '\t', '\n'}:
            if char in line:
                if char == ' ':
                    print('WARNING: char(s) \'{}\' was found in {} and erased'.format(char, line))
                line = line.replace(char, '')
        args += ' ' + line
    return args


def parse_json_dict(args_dict, base):
    results = []
    for k, v in args_dict.items():
        if isinstance(v, dict):
            results += parse_json_dict(v, '{}{}.'.format(base, k))
        else:
            if isinstance(v, str) and v[0] == '[' and v[-1] == ']':
                v = '\"{}\"'.format(v)
            results.append('{}{}={}'.format(base, k, v))
    return results


def read_json(args_lines):
    args_dict = json.loads('\n'.join(args_lines))
    args = 'with ' + ' '.join(parse_json_dict(args_dict, ''))
    return args


def get_exp_lists(config, first_exp_id=1):
    gridargs_list = get_gridargs_list(config.grid)
    exp_name_list, args_list, exp_meta_list = [], [], []
    for args_file in config.files:
        for i, gridargs in enumerate(gridargs_list):
            args, exp_name, script = read_args(args_file)
            args = append_args(args, gridargs, args_file)
            args = append_args(args, config.extra_args, args_file)
            if len(gridargs_list) > 1:
                # TODO: check if this exp does not exist yet
                exp_name += '_v' + str(i+first_exp_id)
            exp_name_list.append(exp_name)
            args_list.append(args)
            exp_meta_list.append(
                {'args_file': args_file,
                 'extra_args': append_args(gridargs, config.extra_args, ''),
                 'script': script,
                 'args': args,
                 'full_command': 'python3 -m {} {}'.format(script, args)})
    return exp_name_list, args_list, exp_meta_list


def get_arg_val_idxs(args, arg_key, json=False):
    if not json:
        # args start with --
        begin_idx = args.find('--' + arg_key) + 2
    else:
        begin_idx = args.find(arg_key)
    end_idx = args[begin_idx:].find(' ')
    if end_idx == -1:
        end_idx = len(args) - begin_idx
    return begin_idx, begin_idx+end_idx


def append_args(args, extra_args, args_file):
    if not extra_args and not args:
        return ''
    if not args or not extra_args:
        return args or extra_args
    if isinstance(extra_args, str):
        extra_args = extra_args.replace('--', '').strip().split(' ')
    for extra_arg in extra_args:
        # if args_file.endswith('.json'):
        #     args = args + ' ' + extra_arg
        #     continue
        arg_key = extra_arg[:extra_arg.find('=')+1]
        if len(extra_arg) > len(arg_key) and len(arg_key) > 0:
            # if the arg is something like --lr=1e-4
            if arg_key in args:
                begin_idx, end_idx = get_arg_val_idxs(args, arg_key, args_file.endswith('.json'))
                args = args[:begin_idx] + extra_arg + args[end_idx:]
            else:
                if not args_file.endswith('.json'):
                    args += ' --' + extra_arg
                else:
                    args += ' ' + extra_arg
        else:
            # if the arg is something like --pudb
            if not args_file.endswith('.json'):
                if ('--' + extra_arg) not in args:
                    args += ' --' + extra_arg
            else:
                if extra_arg not in args:
                    args += ' ' + extra_arg
    return args


def append_log_dir(args, exp_name, seed, args_file, script):
    logdir = os.path.join("/home/apashevi/Logs/agents", exp_name, 'seed%d' % seed)
    if '.json' in args_file:
        scripts2logdir = {'bc.dataset.collect_demos': 'eval.dir',
                          'bc.net.train': 'model.dir',
                          'sim2real.auto.train': 'autoaug.save_dir'}
        assert script in scripts2logdir, 'Script {} does not support json input'.format(script)
        if scripts2logdir[script] not in args:
            args += ' {}={}'.format(scripts2logdir[script], logdir)
    else:
        if '--logdir=' not in args:
            args += ' --logdir=' + logdir
    return args


def get_gridargs_list(grid):
    if not grid:
        return [None]
    gridargs_list = ['']
    grid_dict = collections.OrderedDict(sorted(grid.items()))
    for key, value_list in grid_dict.items():
        assert isinstance(value_list, list) or isinstance(value_list, tuple)
        new_gridargs_list = []
        for gridargs_old in gridargs_list:
            for value in value_list:
                if ' ' in str(value):
                    print('removed spaces from {}, it became {}'.format(
                        value, str(value).replace(' ', '')))
                gridarg = ' --{}={}'.format(key, str(value).replace(' ', ''))
                new_gridargs_list.append(gridargs_old + gridarg)
        gridargs_list = new_gridargs_list
    return gridargs_list
