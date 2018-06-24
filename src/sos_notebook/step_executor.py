#!/usr/bin/env python3
#
# Copyright (c) Bo Peng and the University of Texas MD Anderson Cancer Center
# Distributed under the terms of the 3-clause BSD License.


import time

from sos.hosts import Host
from sos.step_executor import Base_Step_Executor, PendingTasks, Step_Executor
from sos.utils import env, short_repr


class Interactive_Step_Executor(Step_Executor):
    def __init__(self, step, mode='interactive'):
        # This is the only interesting part of this executor. Basically
        # it derives everything from SP_Step_Executor but does not
        # use the Queue mechanism, so the __init__ and the run
        # functions are copied from Base_Step_Executor
        Base_Step_Executor.__init__(self, step)
        self.run_mode = mode
        self.host = None

    def submit_tasks(self, tasks):
        if not tasks:
            return
        if self.host is None:
            if 'queue' in env.sos_dict['_runtime']:
                queue = env.sos_dict['_runtime']['queue']
            elif env.config['default_queue']:
                queue = env.config['default_queue']
            else:
                queue = 'localhost'
            self.host = Host(queue)
        for task in tasks:
            self.host.submit_task(task)

    def wait_for_tasks(self, tasks):
        if not tasks:
            return {}
        # wait till the executor responde
        if all(x == 'completed' for x in self.host.check_status(tasks)):
            if len(tasks) > 4:
                print('sos:: {} task{} completed: {}, {}, ..., {}'.format(
                    len(tasks), 's' if len(tasks) > 1 else '',
                    f"""<a onclick="task_info('{tasks[0]}', '{self.host.alias}')">{tasks[0][:4]}</a>""",
                    f"""<a onclick="task_info('{tasks[1]}', '{self.host.alias}')">{tasks[1][:4]}</a>""",
                    f"""<a onclick="task_info('{tasks[-1]}', '{self.host.alias}')">{tasks[-1][:4]}</a>"""))
            else:
                print('sos:: {} task{} completed: {}'.format(len(tasks), 's' if len(tasks) > 1 else '',
                                                                  ','.join([f"""<a onclick="task_info('{x}', '{self.host.alias}')">{x[:4]}</a>""" for x in tasks])))
            self.host._task_engine.remove_tasks(tasks)
            return self.host.retrieve_results(tasks)
        while True:
            res = self.host.check_status(tasks)
            if all(x not in ('submitted', 'pending', 'running') for x in res):
                #completed = [task for task, status in zip(tasks, res) if status == 'completed']
                self.host._task_engine.remove_tasks(tasks)
                return self.host.retrieve_results(tasks)
            # no pending
            elif not env.config['wait_for_task']:
                raise PendingTasks([(self.host.alias, x) for x, y in zip(tasks, res)
                                    if y in ('pending', 'submitted', 'running')])
            time.sleep(1)

    def run(self):
        return Base_Step_Executor.run(self)

    def log(self, stage=None, msg=None):
        if stage == 'start':
            env.logger.debug('{} ``{}``: {}'.format('Checking' if self.run_mode == 'dryrun' else 'Executing',
                                                    self.step.step_name(), self.step.comment.strip()))
        elif stage == 'input':
            if env.sos_dict['step_input'] is not None:
                env.logger.debug('input:    ``{}``'.format(
                    short_repr(env.sos_dict['step_input'])))
        elif stage == 'output':
            if env.sos_dict['step_output'] is not None:
                env.logger.debug('output:   ``{}``'.format(
                    short_repr(env.sos_dict['step_output'])))
