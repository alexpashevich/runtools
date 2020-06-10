import os
import time
import json
import socket

from random import randint
from runtools.utils.python import cmd
from runtools.settings import OAR_SCRIPT_PATH, OAR_LOG_PATH, LOGIN, JobStatus, MAX_TIMES_RESTART_CRASHED_JOB


class JobMeta(object):
    def __init__(self, run_argv):
        self.run_argv = run_argv
        # Organization settings
        self.name = None
        self.job_id = None
        self.script_filename_key = None
        self._status = JobStatus.WAITING_PREVIOUS
        # Job settings
        self.machine_name = None
        self.besteffort = False
        self.interpreter = 'python'
        self.global_path_project = None
        self.local_path_exe = None
        self.librairies_to_install = []
        self.previous_jobs = []  # type: list[JobMeta]
        # internal pameters to control job restarting (with a manager)
        self.info_settings = {
            'info_path': None, # path to info.json of the job
            'max_wait_time': 1e10, # amount of seconds we can wait maximum for progress increase
            'reported_amount': -1, # last seen job progress (from info.json)
            'reported_time': None, # timestamp when last seen job progress was read
        }
        self.was_restarted_times = 0

    def run(self):
        """
        General pipeline of the run method:
            -If previous jobs have not crashed:
                -A bash script is generated
                -A job is launched to process the bash script we just generated
        """
        # run a job with oarsub (its job_id is retrieved)
        print('Scheduling job {}'.format(self.name))
        print(self.oarsub_command)
        assert self._status == JobStatus.READY_TO_START
        while True:
            try:
                self.job_id = cmd(self.oarsub_command)[-1].split('=')[-1]
                self.link_std()
                print('JOB_ID = {}\n\n\n'.format(self.job_id))
                self._status = JobStatus.SCHEDULED
                break
            except:
                print('Can not connect to {}, retrying in 10 sec...'.format(self.machine_name))
                time.sleep(10)

    def kill_stuck(self):
        print('Killing stuck job {}'.format(self.name))
        assert self._status == JobStatus.STUCK
        while True:
            try:
                oardel_command = 'oardel {}'.format(self.job_id)
                if socket.gethostname() != self.machine_name:
                    oardel_command = "ssh {} ' {} ' ".format(self.machine_name, oardel_command)
                cmd(oardel_command)
                self._status = JobStatus.READY_TO_START
                break
            except:
                print('Can not connect to {}, retrying in 10 sec...'.format(self.machine_name))
                time.sleep(10)

    def restart_crashed(self):
        print('Restarting crashed job {}'.format(self.name))
        assert self._status == JobStatus.CRASHED
        if self.was_restarted_times < MAX_TIMES_RESTART_CRASHED_JOB:
            self.was_restarted_times += 1
            self._status = JobStatus.READY_TO_START
        else:
            print('Job {} was restarted {} times, will not do it anymore'.format(
                self.name, self.was_restarted_times))
            self._status = JobStatus.DONE_FAILURE

    def add_previous_job(self, job):
        assert job not in self.previous_jobs
        self.previous_jobs.append(job)

    def link_std(self):
        for stdname in ['stderr', 'stdout']:
            stdfile = os.path.join(self.oarsub_dirname, '{}_{}.txt'.format(self.job_id, stdname))
            stdfile_link = os.path.join(self.oarsub_dirname, '{}.txt'.format(stdname))
            if os.path.islink(stdfile_link):
                os.unlink(stdfile_link)
            os.symlink(stdfile, stdfile_link)

    """ Management of the bash script, that are fed to oarsub """

    def generate_script(self):
        """
        Generate an executable bash script containing a list of commands
        :param argv: parameters for the script to run
        """
        # build script_dirname if it has not yet been created
        if not os.path.exists(self.script_dirname):
            os.makedirs(self.script_dirname)
        # create script_filename file
        cmd('touch ' + self.script_filename)
        # building the list of commands for the script
        commands = list()
        # install libraries that have been specified
        for library in self.librairies_to_install:
            commands.append('sudo apt-get install ' + library + ' --yes')
        # launch the main exe
        path_exe = os.path.join(self.global_path_project, self.local_path_exe)
        if self.interpreter == '':
            command_script = self.interpreter + path_exe
        else:
            command_script = self.interpreter + ' ' + path_exe
        commands.append(' '.join([command_script] + self.run_argv))
        # script file delete itself when finished
        commands.append('rm ' + self.script_filename + '\n')
        # write into the bash script
        with open(self.script_filename, 'w') as f:
            for command in commands:
                f.write('{0} \n'.format(command))
        # give the permission to the bash script to execute
        cmd('chmod +x ' + self.script_filename)

    @property
    def oarsub_dirname(self):
        assert self.name is not None
        return os.path.join(OAR_LOG_PATH, self.name)

    @property
    def script_dirname(self):
        assert self.name is not None
        return os.path.join(OAR_SCRIPT_PATH, self.name)

    @property
    def get_script_filename(self):
        return os.path.join(self.script_dirname, str(self.script_filename_key) + '.sh')

    @property
    def script_filename(self):
        """
        A script filename must match a single run object
        Therefore each script_filename_nb must be different and have an individual key
        A natural way to define keys would be to iterate
        However, if two jobs with the same job_name create the same key at the time, it would crash
        that's the reason I decided to use a random number to define the key
        :return: a string specifying the path to the bash script
        """
        if self.script_filename_key is None:
            # initializing the script_filename_key
            self.script_filename_key = 0
            while os.path.exists(self.get_script_filename):
                self.script_filename_key = randint(0, 10000)
        return self.get_script_filename

    """ Management of the oarsub command """

    @property
    def oarsub_command(self):
        # make sure that the command will be executed via ssh
        assert socket.gethostname() != self.machine_name
        # Connect to the appropriate machine
        command = "ssh " + self.machine_name + " ' oarsub "
        # Add the running options for oarsub
        command += self.oarsub_options
        # Naming the job
        command += ' --name="' + self.name + '"'
        # Build the oarsub directory
        if not os.path.exists(self.oarsub_dirname):
            os.makedirs(self.oarsub_dirname)
        # Redirecting the stdout and stderr
        stdnames = ['out', 'err']
        stdfiles = [os.path.join(self.oarsub_dirname, '%jobid%_std' + stdname + '.txt') for stdname in stdnames]
        for stdname, stdfile in zip(stdnames, stdfiles):
            command += ' --std' + stdname + '="' + stdfile + '"'
        # Finally add the script to launch
        command += ' "' + self.script_filename + '"'
        command += " '"
        return command

    @property
    def oarsub_options(self):
        options = []
        for symbol, supplementary_options in zip(['p', 'l'], [self.oarsub_p_options, self.oarsub_l_options]):
            if supplementary_options:
                for option in supplementary_options:
                    options.append('-' + symbol + ' "' + option + '"')
        options_string = ' '.join(options)
        if self.besteffort:
            options_string += ' -t besteffort -t idempotent'
        return options_string

    @property
    def oarsub_p_options(self):
        return []

    @property
    def oarsub_l_options(self):
        return []

    """ Job status """

    def info(self):
        if self.info_settings['info_path'] and os.path.exists(self.info_settings['info_path']):
            try:
                job_info = json.load(open(self.info_settings['info_path'], 'r'))[-1]
                return job_info
            except:
                pass
        return None

    def oar_status(self):
        try:
            oarstat_command = 'oarstat -u {}'.format(LOGIN)
            if socket.gethostname() != self.machine_name:
                oarstat_command = "ssh {} ' {} ' ".format(self.machine_name, oarstat_command)
            oarstat_lines = cmd(oarstat_command)
            for line in oarstat_lines:
                if self.job_id in line:
                    status_line = line.split(LOGIN)[0].replace(self.job_id, '').strip()
                    return status_line
        except:
            # we don't really know since we can not connect to the cluster
            pass
        return ''

    def status(self):
        if self._status == JobStatus.WAITING_PREVIOUS:
            previous_jobs_status = [job.status for job in self.previous_jobs]
            if all([job_status == JobStatus.DONE_SUCCESS for job_status in previous_jobs_status]):
                # if all previous jobs have successfully finished, the current job is ready to be launched
                self._status = JobStatus.READY_TO_START
            elif any([job_status == JobStatus.DONE_FAILURE for job_status in previous_jobs_status]):
                # if any of previous jobs has not terminated successfully, the current job can not be launched
                self._status = JobStatus.DONE_FAILURE
        elif self._status == JobStatus.READY_TO_START:
            # the current job is waiting to be launched
            pass
        elif self._status == JobStatus.SCHEDULED:
            # the current job is waiting its turn in OAR scheduling system
            if self.oar_status() == 'R':
                # zero the progress amount to make sure that job is not killed right after it is launched
                self.info_settings['reported_amount'] = -1
                self._status = JobStatus.RUNNING
            else:
                # in theory, the OAR status should be 'W', 'L' or ''
                pass

        elif self._status == JobStatus.RUNNING:
            # the current job is running on the cluster
            if self.oar_status() != 'R':
                # zero the progress amount to make sure that job is not killed right after it is launched
                self.info_settings['reported_amount'] = -1
                self._status = JobStatus.SCHEDULED
            else:
                # self.script_filename should be erased at the end of job script, check if it still exists
                job_has_terminated = not os.path.exists(self.script_filename)
                # read info.json of the job with job progress status
                job_info = self.info()
                if job_info:
                    if job_has_terminated:
                        # the job has terminated so it has either crashed or completed
                        if job_info['progress'] >= job_info['total']:
                            self._status = JobStatus.DONE_SUCCESS
                        elif job_info['progress'] == 0:
                            # the job has terminated without any progress, probably it means that the code is corrput
                            self._status = JobStatus.DONE_FAILURE
                        else:
                            # the job has crashed after making some progress, maybe we will restart it later
                            self._status = JobStatus.CRASHED
                    else:
                        # check if the job has stuck
                        time_now = time.time()
                        if job_info['progress'] > self.info_settings['reported_amount']:
                            self.info_settings['reported_amount'] = job_info['progress']
                            self.info_settings['reported_time'] = time_now
                        elif time_now - self.info_settings['reported_time'] > self.info_settings['max_wait_time']:
                            self.info_settings['reported_amount'] = -1
                            self._status = JobStatus.STUCK
                elif job_has_terminated:
                    # info.json was not created but the job has terminated
                    self._status = JobStatus.CRASHED

        elif self._status == JobStatus.STUCK:
            # the current job is stuck, it should be restarted in an outer function
            pass
        elif self._status == JobStatus.CRASHED:
            # the current job has crashed, nothing to be done here
            pass
        elif self._status == JobStatus.DONE_FAILURE:
            # the current job has completely crashed, nothing to be done here
            pass
        elif self._status == JobStatus.DONE_SUCCESS:
            # the current job has successfully completed, nothing to be done here
            pass
        return self._status
