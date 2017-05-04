import sys
from run.skeleton_sequences.job_deep_learning import train_val_test_runs
from run.job_manager import manage
from argument_generator import main_argv, run_prefix_suffix
from itertools import product

jobs = []

only_initialization = False
only_evaluating = False
""" COPY AREA"""
run_prefix = 'vch_2_va_baseline'
idxs = [['ntu_cs_3D'], ['s_trans'], ['joint'], [0], [0]]
# idxs = [['ntu_cs_2D'], ['ntu_cs_2D'], ['joint'], [1], [0]]

restore = False
restore_run_dir = 'two_stream_clip_mem-learning_rate0.0001-clip_gradient_norm1_1'
restore_checkpoint_filename = '4500'

# Training setting
for idx in product(*idxs):
    argv1 = main_argv(*idx)
    argv1.extend(['run_prefix=' + run_prefix, 'training_steps=1000000', 'summary_flush_rate=100', 'checkpoint_rate=100'])

    # Training hyperparameters
    # TODO: add type of prediction, and regularization parameter
    for batch_size, learning_rate, actors_nb, mirror, switch, worst_prediction_nb in product([256], [5e-3], [2], [False], [False], [1]):
        argv2 = argv1[:] + ['batch_size=' + str(batch_size), 'learning_rate=' + str(learning_rate)]
        argv2 += ['rnn_dropout_prob=0.5']
        # argv2 += ['mirroring_left_right=' + str(mirror), 'switching_main_second_actor=' + str(switch)]
        # argv2 += ['prediction_type=inattention', 'worst_prediction_nb=' + str(worst_prediction_nb)]

        # Model hyperparameters
        for rnn_units, rnn_layers, rnn_type in product([100], [3], ['basic_lstm', 'lstm']):
            argv3 = argv2[:]
            argv3.extend(['rnn_units=' + str(rnn_units), 'rnn_layers=' + str(rnn_layers), 'rnn_type=' + rnn_type])

            """ END COPY AREA """

            # Extend the list of runs
            # Train argv
            train_run_argv = argv3 + ['run_prefix=' + run_prefix]
            if restore:
                train_run_argv.append('restore_run_dir=' + restore_run_dir)
                train_run_argv.append('restore_checkpoint_filename=' + restore_checkpoint_filename)
            # Evaluation argv
            job_name = run_prefix + run_prefix_suffix(argv3)
            evaluation_run_argv = argv3 + ['run_prefix=' + job_name]
            jobs.extend(train_val_test_runs(train_run_argv, evaluation_run_argv, job_name,
                                            machine='gpu', only_evaluating=only_evaluating))

manage(jobs, only_initialization=only_initialization)
