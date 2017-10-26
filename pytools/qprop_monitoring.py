import subprocess as sp
import os, sys
from pytools.tools import cmd
from settings import LOGIN, CPU_MACHINE, GPU_MACHINE, SHARED_CPU_MACHINE, OARSUB_DIRNAME
import curses
import argparse


stdscr = curses.initscr()
KEYWORDS = ['AverageReturn', 'MaxReturn', 'MinDist', 'srS1', 'srS2', 'srG1', 'srG2']
MAX_LENGTH = 80
NB_DECIMAL = 3

def tail(f, n):
    assert n >= 0
    pos, lines = n+1, []
    while len(lines) <= n:
        try:
            f.seek(-pos, 2)
        except IOError:
            f.seek(0)
            break
        finally:
            lines = list(f)
        pos *= 2
    return lines[-n:]

def report_progress(machine_to_jobs_summary):
    """ Print nice formatted output using unix curses. """
    stdscr.clear()
    stdscr.addstr(0, 0, 'Monitoring...')
    counter = 1
    for machine, jobs_summary in machine_to_jobs_summary.items():
        stdscr.addstr(counter, 0, '### ' + machine + ' ###')
        counter += 1
        if len(jobs_summary) > 0:
            lengths = []
            template_length = len(jobs_summary[0])
            for i in range(template_length):
                lengths.append(min(max([len(x[i]) for x in jobs_summary]), MAX_LENGTH))

            template = ""
            for i in range(template_length):
                template += "{%i:%i}" % (i, lengths[i])
                if i != template_length - 1:
                    template += ' | '

            for job in jobs_summary:
                for i in range(len(job)):
                    if len(job[i]) > MAX_LENGTH:
                        job[i] = job[i][-MAX_LENGTH:]

            for i in range(len(jobs_summary)):
                line = template.format(*jobs_summary[i])
                stdscr.addstr(counter + i, 0, line)
            counter += len(jobs_summary)
        else:
            stdscr.addstr(counter, 0, 'No jobs running\n')
            counter += 2
    stdscr.refresh()


""" Monitor only the master"""

def cut_value(string, keyword):
    try:
        begin = string.find(keyword)
        end = string[begin:].find('\n')
        string_temp = string[begin: begin + end]
        last_space = string_temp.rfind(' ')
        value = string_temp[last_space + 1:]
        if value.find('.') > 0 and value.find('.') + NB_DECIMAL < len(value):
            value = value[:value.find('.') + NB_DECIMAL]
        if len(value) > 15:
            return 'n/a'
        return value
    except:
        return 'n/a'


# TODO: delete (depricated)
def cut_itr(string):
    try:
        begin = string.rfind('itr #')
        string_temp = string[begin + 5:]
        end = string_temp.find('|')
        itr = string_temp[:end - 1].strip()
        if len(itr) > 15:
            return 'n/a'
        return itr
    except:
        return 'n/a'

def cut_step(string):
    try:
        substring = 'global step '
        begin = string.rfind(substring)
        string_temp = string[begin + len(substring):]
        end = string_temp.find(')')
        step = string_temp[:end].strip()
        if len(step) > 15:
            return 'n/a'
        if len(step) > 3:
            step = step[:-3] + 'K'
        return step
    except:
        return 'n/a'

def monitor(argv):
    ''' Monitor only the master. '''
    # initialize unix curses
    curses.noecho()
    curses.cbreak()

    # initialize argparser
    parser = argparse.ArgumentParser()
    parser.add_argument('--sleep', type=int, default=10,
                        help='Seconds to sleep')
    args = parser.parse_args(argv[1:])

    try:
        while True:
            clear_list, edgar_list = [], []
            machines = [CPU_MACHINE, GPU_MACHINE, SHARED_CPU_MACHINE]
            machine_to_jobs_summary = {machine: [] for machine in machines}
            for machine in machines:
                try:
                    jobs = cmd("ssh -x " + machine + " 'oarstat | grep " + LOGIN + "'")
                except sp.CalledProcessError as e:
                    continue

                job_list_titles = ['job_name', 'job_id', 'time', 'itr'] + KEYWORDS
                machine_to_jobs_summary[machine].append(job_list_titles)
                for job in sorted(jobs):
                    # Monitoring only non interactive jobs
                    if (job.split(' ')[-2]).split('J=')[-1] == 'I':
                        continue
                    # Extracting information and initializing a list for printing
                    job_id = job.split(' ')[0]
                    job_name = ''
                    if len(job.split('N=')) > 1 and len((job.split('N=')[1]).split(' (')) > 0:
                        job_name = (job.split('N=')[1]).split(' (')[0]
                        if len(job_name.split(',')) > 1:
                            job_name = job_name.split(',')[0]
                    duration = (job.split(' R=')[0]).split(' ')[-1]
                    job_list = [job_name, job_id, duration]
                    # oarout = os.path.join(OARSUB_DIRNAME, job_name, job_id + '_stdout.txt')
                    oarout = os.path.join(OARSUB_DIRNAME, job_name, job_id + '_stderr.txt')
                    try:
                        oarout_list = tail(open(oarout, 'r'), 70)
                    except:
                        continue

                    oarout_string = ' '.join(oarout_list)
                    job_list.append(cut_step(oarout_string))
                    for keyword in KEYWORDS:
                        job_list.append(cut_value(oarout_string, keyword))
                        # TODO: fix cutting when a job has just started
                    machine_to_jobs_summary[machine].append(job_list)

            # TODO: refactor
            if len(machine_to_jobs_summary['clear']) > 0:
                jobs_clear = [machine_to_jobs_summary['clear'][0]] + sorted(machine_to_jobs_summary['clear'][1:])
                machine_to_jobs_summary['clear'] = jobs_clear
            report_progress(machine_to_jobs_summary)
            # Possibility to configure the refreshing time lapse, by passing an argument
            cmd('sleep {}'.format(args.sleep))
    finally:
        # kill unix curses in order to have normal termial output afterwards
        curses.echo()
        curses.nocbreak()
        curses.endwin()


if __name__ == '__main__':
    monitor(sys.argv)
