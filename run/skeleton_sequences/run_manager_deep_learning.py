import sys
from run.skeleton_sequences.run_deep_learning import train_val_test_runs
from run.run_manager import manage

sys.path.append('/home/lear/erleroux/src/skeleton_sequences')
from tensorflow_runs.argument_generator import main_argv, run_prefix_suffix


from itertools import product


runs = []

""" COPY AREA"""
run_prefix = 'two_stream_we'
idxs = [[0], [1], [1], [1]]

restore = False
restore_run_dir = 'two_stream_new-learning_rate0.0001-clip_gradient_norm0_1'
restore_checkpoint_filename = '4000'

# Training setting
for idx in product(*idxs):
    argv1 = main_argv(*idx)
    argv1.extend(['run_prefix=' + run_prefix, 'training_steps=10000', 'summary_flush_rate=50', 'checkpoint_rate=1000'])

    # Training hyperparameters
    # TODO: add type of prediction, and regularization parameter
    for batch_size, learning_rate, dropout_prob, clip_gradient_norm in product([256], [5e-3, 5e-4], [0.5], [0]):
        argv2 = argv1[:] + ['batch_size=' + str(batch_size), 'learning_rate=' + str(learning_rate)]
        argv2 += ['clip_gradient_norm=' + str(clip_gradient_norm)]

        # Model hyperparameters
        for rnn_units, rnn_layers, rnn_type in product([100, 300], [2, 4], ['gru', 'lstm']):
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
            runs.extend(train_val_test_runs(train_run_argv, evaluation_run_argv, job_name,
                                            machine='gpu', only_evaluating=False))
# print(len(runs) / 3)
manage(runs)
