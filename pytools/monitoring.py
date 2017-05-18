import subprocess as sp
import os, sys
from pytools.tools import cmd
from settings import LOGIN, OARSUB_DIRNAME
import curses
import argparse


stdscr = curses.initscr()
keywords = ['MaxReturn', 'AverageReturn', 'AvgLifted']
MAX_LENGTH = 80


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

def report_progress(clear_list, edgar_list):
    ''' Print nice formatted output using unix curses. '''
    stdscr.clear()
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
            lengths = []
            template_length = len(machine_list[0])
            for i in range(template_length):
                lengths.append(min(max([len(x[i]) for x in machine_list]), MAX_LENGTH))

            template = ""
            for i in range(template_length):
                template += "{%i:%i}" % (i, lengths[i])
                if i != template_length - 1:
                    template += ' | '

            for el in machine_list:
                for i in range(len(el)):
                    if len(el[i]) > MAX_LENGTH:
                        el[i] = el[i][-MAX_LENGTH:]

            for i in range(len(machine_list)):
                line = template.format(*machine_list[i])
                stdscr.addstr(counter + i, 0, line)
            counter += len(machine_list)
        else:
            stdscr.addstr(counter, 0, 'No jobs running\n')
            counter += 2
    stdscr.refresh()


def cut_value(string, keyword):
    try:
        begin = string.rfind(keyword)
        end = string[begin:].find('\n')
        string_temp = string[begin: begin + end]
        last_space = string_temp.rfind(' ')
        return string_temp[last_space + 1:]
    except:
        return 'n/a'


def cut_itr(string):
    try:
        begin = string.rfind('itr #')
        string_temp = string[begin + 5:]
        end = string_temp.find('|')
        return string_temp[:end - 1]
    except:
        return 'n/a'


def monitor(argv):
    ''' Monitor only the master. '''
    # initialize unix curses
    curses.noecho()
    curses.cbreak()

    # initialize argparser
    parser = argparse.ArgumentParser()
    parser.add_argument('--qprop', type=bool, default=False,
                        help='Whether qprop is running, if True, iter number will be displayed.')
    args = parser.parse_args(argv[1:])

    try:
        while True:
            clear_list, edgar_list = [], []
            for machine in ['edgar', 'clear']:
                try:
                    jobs = cmd("ssh -x " + machine + " 'oarstat | grep " + LOGIN + "'")
                except sp.CalledProcessError as e:
                    jobs = []
                if jobs != []:
                    if args.qprop:
                        job_list_titles = ['job_name',
                                           'job_id',
                                           'time',
                                           'itr'] + keywords
                        if machine == 'edgar':
                            edgar_list.append(job_list_titles)
                        else:
                            clear_list.append(job_list_titles)
                    for job in jobs:
                        # Monitoring only non interactive jobs
                        if (job.split(' ')[-2]).split('J=')[-1] != 'I':
                            # Extracting information and initializing a list for printing
                            job_id = job.split(' ')[0]
                            job_name = ''
                            if len(job.split('N=')) > 1 and len((job.split('N=')[1]).split(' (')) > 0:
                                job_name = (job.split('N=')[1]).split(' (')[0]
                            duration = (job.split(' R=')[0]).split(' ')[-1]
                            job_list = [job_name, job_id, duration]
                            if args.qprop:
                                oarout = os.path.join(OARSUB_DIRNAME, job_name, job_id + '_stdout.txt')
                                oarout_list = tail(open(oarout, 'r'), 70)
                                oarout_string = ' '.join(oarout_list)
                                job_list.append(cut_itr(oarout_string))
                                for keyword in keywords:
                                    job_list.append(cut_value(oarout_string, keyword))

                            if machine == 'edgar':
                                edgar_list.append(job_list)
                            else:
                                clear_list.append(job_list)

                        # with this kind of stuff we can open the OAR file:

            report_progress(clear_list, edgar_list)
            # Possibility to configure the refreshing time lapse
            # if len(argv) > 1:
            #     cmd('sleep ' + argv[1])
            # else:
            cmd('sleep 10')
    finally:
        # kill unix curses in order to have normal termial output afterwards
        curses.echo()
        curses.nocbreak()
        curses.endwin()


if __name__ == '__main__':
    monitor(sys.argv)
