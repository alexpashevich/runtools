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
    parser.add_argument('--task', '-t', action='store_true', default=False)
    parser.add_argument('--select_only', '-so', action='store_true', default=False)
    parser.add_argument('--split', '-sp', type=str, default='valid_seen')
    args = parser.parse_args()
    return args


def main():
    args = get_args()
    eval_type = 'task' if args.task else 'subgoal'
    # TODO: also print fast evals
    eval_mode = 'normal'
    exp_results = {}
    seed_results_best = {}
    for exp_path in args.exps:
        eval_json_path = os.path.join(exp_path, 'eval.json')
        with open(eval_json_path) as f:
            eval_json = json.load(f)
        for eval_epoch, eval_dict in eval_json.items():
            try:
                results = eval_dict[args.split][eval_type][eval_mode]['results']
                epoch_path = os.path.join(exp_path, eval_epoch)
                print('Loaded evaluation of {}'.format(epoch_path))
                # prepare the string to be printed
                if args.task:
                    results = results['all']
                    sr_avg = results['success']['success_rate'] * 100
                    sr_plw_avg = results['path_length_weighted_success_rate'] * 100
                    gc_sr = results['goal_condition_success']['goal_condition_success_rate']
                    results_str = 'GC = {:.1f}%'.format(gc_sr * 100)
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
                exp_results[epoch_path] = {
                    'sr': sr_avg, 'plw': sr_plw_avg, 'str': results_str.strip(', ')}
                # prepare results for mean/std exp comparison
                exp_name = os.path.basename(exp_path)
                if exp_name not in seed_results_best:
                    seed_results_best[exp_name] = sr_avg
                if sr_avg > seed_results_best[exp_name]:
                    seed_results_best[exp_name] = sr_avg
            except:
                pass

    exp_results_sorted = sorted(exp_results.items(), key=lambda x: -x[1]['sr'])
    for exp_name, exp_dict in exp_results_sorted:
        print(colored('Exp {} (avg SR = {:.1f}%, avg SRPLW = {:.1f}%): {}'.format(
            exp_name, exp_dict['sr'], exp_dict['plw'], exp_dict['str']), 'green'))

    # print mean/std comparison
    if seed_results_best:
        print('\n\n\n')
        exp_results_best = collections.defaultdict(list)
        for seed_name, seed_sr in seed_results_best.items():
            exp_name = '_'.join(seed_name.split('_')[:-1])
            exp_results_best[exp_name].append(seed_sr)
            exp_results_best_sorted = sorted(exp_results_best.items(), key=lambda x: -np.mean(x[1]))
        for exp_name, exp_srs in exp_results_best_sorted:
            print(colored('Exp {}: {:.1f} +/- {:.1f}'.format(
                exp_name, np.mean(exp_srs), np.std(exp_srs)), 'cyan'))


if __name__ == '__main__':
    main()
