import os
import json
import glob
import argparse
from termcolor import colored

ALL_SUBGOALS = ['GotoLocation', 'PickupObject', 'PutObject', 'CoolObject', 'HeatObject', 'CleanObject', 'SliceObject', 'ToggleObject']

def get_args():
    parser = argparse.ArgumentParser()
    # experiments to load results from
    parser.add_argument('exps', type=str, nargs='+')
    # whether to look for a subgoals evaluation (by default task evaluation)
    parser.add_argument('--task', '-t', action='store_true', default=False)
    args = parser.parse_args()
    return args


def main():
    args = get_args()

    prefix = 'task' if args.task else 'subgoal'
    exp_results = {}
    for exp_path in args.exps:
        eval_jsons = sorted(glob.glob(os.path.join(exp_path, '{}_results*.json'.format(prefix))))
        for eval_json in eval_jsons:
            try:
                results = json.load(open(eval_json))['results']
                eval_name = eval_json.split('task_results_')[-1]
                exp_name = eval_json.split('/')[-2]
                print('Loaded evaluation from {}'.format(eval_json))
                if args.task:
                    gc_sr = results['all']['goal_condition_success']['goal_condition_success_rate']
                    task_sr = results['all']['success']['success_rate']
                    # print(colored("Exp %s: SR = %.1f%%, GC = %.1f%%" % (
                    #     exp_name, task_sr * 100, gc_sr * 100), 'green'))
                    sr_all = results['all']['success']['success_rate'] * 100
                    results_str = 'SR = %.1f%%, GC = %.1f%%' % (task_sr * 100, gc_sr * 100)
                else:
                    # print(colored("Exp {}".format(exp_name), 'green'))
                    sr_sum, sr_count, results_str = 0, 0, '\n'
                    for sg_name, sg_dict in sorted(results.items()):
                        # print(colored("Subgoal %s: SR = %.1f%%" % (sg_name, sg_dict['sr'] * 100), 'yellow'))
                        results_str += "%s: %.1f%%, " % (sg_name, sg_dict['sr'] * 100)
                        # sr_all += sg_dict['sr'] * 100
                        sr_sum += sg_dict['successes']
                        sr_count += sg_dict['evals']
                    sr_all = sr_sum / sr_count * 100
                # exp_results[exp_name] = {'all': sr_all, 'str': results_str.strip(', ')}
                exp_results[eval_json] = {'all': sr_all, 'str': results_str.strip(', ')}
            except:
                print(colored('Evaluation {} is corrupt'.format(eval_json), 'red'))
                continue

    exp_results_sorted = sorted(exp_results.items(), key=lambda x: -x[1]['all'])
    for exp_name, exp_dict in exp_results_sorted:
        print(colored('Exp {} (avg {:.1f}%): {}'.format(exp_name, exp_dict['all'], exp_dict['str']), 'green'))

if __name__ == '__main__':
    main()
