import sys
from run.skeleton_sequences.job_deep_learning import train_val_test_runs
from run.job_manager import manage

sys.path.append('/home/lear/erleroux/src/skeleton_sequences')
from tensorflow_runs.argument_generator import main_argv, run_prefix_suffix


from itertools import product


jobs = []

only_evaluating = False
""" COPY AREA"""
run_prefix = 'mo_ablation_batsiz'
idxs = [[0], [0], [1], [0]]

restore = False
restore_run_dir = 'two_stream_clip_mem-learning_rate0.0001-clip_gradient_norm1_1'
restore_checkpoint_filename = '4500'



# Training setting
for idx in product(*idxs):
    argv1 = main_argv(*idx)
    argv1.extend(['run_prefix=' + run_prefix, 'training_steps=1000000', 'summary_flush_rate=10', 'checkpoint_rate=100'])

    # Training hyperparameters
    # TODO: add type of prediction, and regularization parameter
    for batch_size, learning_rate, rnn_dropout_prob, clip_gradient_norm in product([256], [1e-3], [1], [0.25]):
        argv2 = argv1[:] + ['batch_size=' + str(batch_size), 'learning_rate=' + str(learning_rate)]
        argv2 += ['clip_gradient_norm=' + str(clip_gradient_norm), 'rnn_dropout_prob=' + str(rnn_dropout_prob)]

        # Model hyperparameters
        for rnn_units, rnn_layers, rnn_type in product([100], [2], ['gru']):
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
# print(len(runs) / 3)
manage(jobs, only_initialization=False)
