import subprocess as sp
import os, sys
from pytools.tools import cmd
from settings import LOGIN, OARSUB_DIRNAME
import curses

def report_progress(clear_list, edgar_list):
    ''' Print nice formatted output using unix curses. '''
    stdscr.addstr(0, 0, 'Monitoring...')
    counter = 1
    for machine in ['edgar', 'clear']:
        stdscr.addstr(counter, 0, '### ' + machine + ' ###')
        counter += 1
        if machine == 'edgar':
            machine_list = edgar_list
        else:
            machine_list = clear_list
        if len(machine_list) > 0:
            max_name_length = max([len(x[0]) for x in machine_list])
            max_number_length = max([len(x[1]) for x in machine_list])
            max_duration_length = max([len(x[2]) for x in machine_list])
            template = "{0:%i} | {1:%i} | {2:%i}" % (max_name_length,
                                                    max_number_length,
                                                    max_duration_length)
            for i in range(len(machine_list)):
                line = template.format(*machine_list[i])
                stdscr.addstr(counter + i, 0, line)
            counter += len(machine_list)
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
            for machine in ['edgar', 'clear']:
                try:
                    jobs = cmd("ssh " + machine + " 'oarstat | grep " + LOGIN + "'")
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
                            if machine == 'edgar':
                                edgar_list.append([job_name, job_number, duration])
                            else:
                                clear_list.append([job_name, job_number, duration])

                            # TODO:Let user write function to parse the OAR files, and display information during monitoring

            report_progress(clear_list, edgar_list)
            # Possibility to configure the refreshing time lapse
            if len(sys.argv) > 1:
                cmd('sleep ' + sys.argv[1])
            else:
                cmd('sleep 10')
    finally:
        curses.echo()
        curses.nocbreak()
        curses.endwin()
