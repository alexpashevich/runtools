import os
import json
import glob
import argparse
import collections
import numpy as np
from termcolor import colored

ALL_SUBGOALS = ['GotoLocation', 'PickupObject', 'PutObject', 'CoolObject', 'HeatObject', 'CleanObject', 'SliceObject', 'ToggleObject']

def get_args():
    parser = argparse.ArgumentParser()
    # experiments to load results from
    parser.add_argument('exps', type=str, nargs='+')
    # whether to look for a subgoals evaluation (by default task evaluation)
    parser.add_argument('--subgoal', '-sg', action='store_true', default=False)
    parser.add_argument('--select_only', '-so', action='store_true', default=False)
    parser.add_argument('--fast_eval', '-f', action='store_true', default=False)
    parser.add_argument('--print_each_exp', '-p', action='store_true', default=False)
    parser.add_argument('--split_train', '-spt', action='store_true', default=False)
    parser.add_argument('--split_unseen', '-spu', action='store_true', default=False)
    parser.add_argument('--dataset', '-d', default=None)
    args = parser.parse_args()
    args.task = not args.subgoal
    return args

def get_sr_dict(results, task_eval):
    if task_eval:
        results = results['all']
        sr_avg = results['success']['success_rate'] * 100
        sr_plw_avg = results['path_length_weighted_success_rate'] * 100
        gc_sr = results['goal_condition_success']['goal_condition_success_rate']
        results_str = 'GC = {:.1f}%'.format(gc_sr * 100)
        sr_count = results['success']['num_evals']
    else:
        sr_sum, sr_plw_sum, sr_count, results_str = 0, 0, 0, '\n'
        for sg_name, sg_dict in sorted(results.items()):
            results_str += '{}: {:.1f}% ({:.1f}%), '.format(
                sg_name, sg_dict['sr'] * 100, sg_dict['sr_plw'] * 100)
            sr_sum += sg_dict['sr'] * sg_dict['evals']
            sr_plw_sum += sg_dict['sr_plw'] * sg_dict['evals']
            sr_count += sg_dict['evals']
        sr_avg = sr_sum / sr_count * 100
        sr_plw_avg = sr_plw_sum / sr_count * 100
    sr_dict = {
        'sr': sr_avg,
        'plw': sr_plw_avg,
        'str': results_str.strip(', '),
        'num': sr_count}
    return sr_dict


def main():
    args = get_args()
    eval_type = 'task' if args.task else 'subgoal'
    eval_mode = 'fast_eval' if args.fast_eval else 'normal'

    if args.dataset is not None:
        split = 'valid_seen'
        if args.split_unseen:
            assert not args.split_train
            split = 'valid_unseen'
        elif args.split_train:
            assert not args.split_unseen
            split = 'train'
        if args.dataset.startswith('lmdb/'):
            args.dataset = args.dataset.replace('lmdb/', 'lmdb:')
        elif 'lmdb' not in args.dataset:
            args.dataset = 'lmdb:' + args.dataset
        user_split = '{}:{}'.format(split, args.dataset)
    else:
        user_split = None

    exp_results_all = collections.defaultdict(dict)
    seed_results_best_all = collections.defaultdict(dict)
    for exp_path in args.exps:
        eval_json_path = os.path.join(exp_path, 'eval.json')
        if not os.path.exists(eval_json_path):
            continue
        with open(eval_json_path) as f:
            eval_json = json.load(f)
        for eval_epoch, eval_dict in eval_json.items():
            for eval_data, eval_split in eval_dict.items():
                if user_split is not None and eval_split != user_split:
                    continue
                eval_data = eval_data.replace(';lang', '')
                if eval_type not in eval_split or eval_mode not in eval_split[eval_type]:
                    continue
                results = eval_split[eval_type][eval_mode]['results']
                epoch_path = os.path.join(exp_path, eval_epoch)
                # prepare the string to be printed
                sr_dict = get_sr_dict(results, args.task)
                exp_results_all[eval_data][epoch_path] = sr_dict
                # prepare results for mean/std exp comparison
                exp_name = os.path.basename(exp_path)

                if exp_name not in seed_results_best_all[eval_data]:
                    seed_results_best_all[eval_data][exp_name] = (sr_dict['sr'], sr_dict['plw'])
                if sr_dict['sr'] > seed_results_best_all[eval_data][exp_name][0]:
                    seed_results_best_all[eval_data][exp_name] = (sr_dict['sr'], sr_dict['plw'])

    for eval_data, exp_results in sorted(exp_results_all.items()):
        print(colored('\nEvaluated on {}:'.format(eval_data), 'blue'))
        exp_results_sorted = sorted(exp_results.items(), key=lambda x: -x[1]['sr'])
        if args.print_each_exp:
            for exp_name, exp_dict in exp_results_sorted:
                print(colored('Exp {} (avg SR = {:.1f}%, avg SRPLW = {:.1f}%, num trials {}): {}'.format(
                    exp_name, exp_dict['sr'], exp_dict['plw'], exp_dict['num'], exp_dict['str']), 'green'))
            print('')
        # print mean/std comparison
        if seed_results_best_all[eval_data]:
            exp_srs = collections.defaultdict(list)
            exp_srs_plw = collections.defaultdict(list)
            for seed_name, (seed_sr, seed_sr_plw) in seed_results_best_all[eval_data].items():
                exp_name = '_'.join(seed_name.split('_')[:-1])
                exp_srs[exp_name].append(seed_sr)
                exp_srs_plw[exp_name].append(seed_sr_plw)
            exp_srs_sorted = sorted(exp_srs.items(), key=lambda x: -np.mean(x[1]))
            for exp_name, exp_srs in exp_srs_sorted:
                print(colored('Exp {} ({} seeds): {:.2f} +/- {:.2f} ({:.2f} +/- {:.2f})'.format(
                    exp_name, len(exp_srs),
                    np.mean(exp_srs), np.std(exp_srs),
                    np.mean(exp_srs_plw[exp_name]), np.std(exp_srs_plw[exp_name])), 'cyan'))


if __name__ == '__main__':
    main()
