import sys
from run.example.job_example import JobExample
from run.job_manager import manage


def single_run(argv):
    JobExample(argv).run()


def double_run(argv):
    # Defining runs
    root_run = JobExample(argv)
    root_run.job_name = 'root'
    child_run = JobExample(argv)
    child_run.job_name = 'child'
    runs = [root_run, child_run]
    # Defining dependencies
    child_run.add_previous_job(root_run)
    # Running
    manage(runs)


def fork_run(argv):
    # Defining runs
    root_run = JobExample(argv)
    root_run.job_name = 'root'
    child1_run = JobExample(argv)
    child1_run.job_name = 'child1'
    child2_run = JobExample(argv)
    child2_run.job_name = 'child2'
    runs = [root_run, child1_run, child2_run]
    # Defining dependencies
    child1_run.add_previous_job(root_run)
    child2_run.add_previous_job(root_run)
    # Running
    manage(runs, only_initialization=False)


if __name__ == '__main__':
    # single_run(sys.argv[1:])
    # double_run(sys.argv[1:])
    fork_run(sys.argv[1:])

