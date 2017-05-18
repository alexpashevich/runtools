import subprocess as sp
import os, sys
from pytools.tools import cmd
from settings import LOGIN, CPU_MACHINE, GPU_MACHINE, OARSUB_DIRNAME
import curses


def report_progress(machine_to_jobs_summary):
    """ Print nice formatted output using unix curses. """
    stdscr.clear()
    stdscr.addstr(0, 0, 'Monitoring...')
    counter = 1
    for machine, jobs_summary in machine_to_jobs_summary.items():
        stdscr.addstr(counter, 0, '### ' + machine + ' ###')
        counter += 1
        if len(jobs_summary) > 0:
            max_name_length = max([len(x[0]) for x in jobs_summary])
            max_number_length = max([len(x[1]) for x in jobs_summary])
            max_duration_length = max([len(x[2]) for x in jobs_summary])
            template = "{0:%i} | {1:%i} | {2:%i}" % (max_name_length,
                                                     max_number_length,
                                                     max_duration_length)
            for i in range(len(jobs_summary)):
                line = template.format(*jobs_summary[i])
                stdscr.addstr(counter + i, 0, line)
            counter += len(jobs_summary)
        else:
            stdscr.addstr(counter, 0, 'No jobs running\n')
            counter += 2
    stdscr.refresh()


""" Monitor only the master"""

if __name__ == '__main__':
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()

    try:
        while True:
            clear_list, edgar_list = [], []
            machines = [CPU_MACHINE, GPU_MACHINE]
            machine_to_jobs_summary = {machine: [] for machine in machines}
            for machine in machines:
                try:
                    jobs = cmd("ssh -X -Y " + machine + " 'oarstat | grep " + LOGIN + "'")
                except sp.CalledProcessError as e:
                    jobs = []
                if jobs != []:
                    for job in jobs:
                        # Monitoring only non interactive jobs
                        if (job.split(' ')[-2]).split('J=')[-1] != 'I':
                            # Extracting information and initializing a list for printing
                            job_number = job.split(' ')[0]
                            job_name = ''
                            if len(job.split('N=')) > 1 and len((job.split('N=')[1]).split(' (')) > 0:
                                job_name = (job.split('N=')[1]).split(' (')[0]
                            duration = (job.split(' R=')[0]).split(' ')[-1]
                            machine_to_jobs_summary[machine].append([job_name, job_number, duration])

                            # TODO:Let user write function to parse the OAR files, and display information during monitoring
                            # with this kind of stuff we can open the OAR file:
                            # os.path.join(OARSUB_DIRNAME, job_name, job_id + 'stderr')

            report_progress(machine_to_jobs_summary)
            # Possibility to configure the refreshing time lapse, by passing an argument
            cmd('sleep ' + sys.argv[1] if len(sys.argv) > 1 else 10)

    finally:
        curses.echo()
        curses.nocbreak()
        curses.endwin()
