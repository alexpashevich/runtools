import os
import json

from runtools.settings import SCRIPT_TO_LOGDIR


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

    args = read_json(good_args_lines)
    return args, exp_name, script


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


def _get_argument_value_idxs(args, arg_key):
    begin_idx = args.find(arg_key)
    end_idx = args[begin_idx:].find(' ')
    if end_idx == -1:
        end_idx = len(args) - begin_idx
    return begin_idx, begin_idx+end_idx


def append_args(args, extra_args):
    if not extra_args and not args:
        return ''
    if not args or not extra_args:
        return args or extra_args
    if isinstance(extra_args, str):
        extra_args = extra_args.replace('--', '').strip().split(' ')
    for extra_arg in extra_args:
        arg_key = extra_arg[:extra_arg.find('=')+1]
        if len(extra_arg) > len(arg_key) and len(arg_key) > 0:
            # if the arg is something like --lr=1e-4
            if arg_key in args:
                begin_idx, end_idx = _get_argument_value_idxs(args, arg_key)
                args = args[:begin_idx] + extra_arg + args[end_idx:]
            else:
                args += ' ' + extra_arg
        else:
            # if the arg is something like --pudb
            if extra_arg not in args:
                args += ' ' + extra_arg
    return args


def append_log_dir(args, exp_name, seed, args_file, script):
    assert '.json' in args_file
    assert script in SCRIPT_TO_LOGDIR, 'Script {} is not supported'.format(script)
    if SCRIPT_TO_LOGDIR[script] in args:
        print('Logdir was already specified, overwriting it')
    args = append_args(
        args, ['{}={}'.format(SCRIPT_TO_LOGDIR[script], exp_name)])
    return args
