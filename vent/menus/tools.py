import npyscreen
import time

from threading import Thread

from vent.api.actions import Action
from vent.helpers.logs import Logger
from vent.helpers.meta import Containers
from vent.helpers.meta import Images


class ToolForm(npyscreen.ActionForm):
    """ Tools form for teh Vent CLI """
    def __init__(self, *args, **keywords):
        """ Initialize tool form objects """
        self.logger = Logger(__name__)
        self.logger.info(str(keywords['names']))
        api_action = Action()
        action = {'api_action': api_action}
        self.tools_tc = {}
        if keywords['action_dict']:
            action.update(keywords['action_dict'])
        if keywords['names']:
            i = 1
            for name in keywords['names']:
                action['action_object'+str(i)] = getattr(api_action, name)
                i += 1
        self.action = action
        super(ToolForm, self).__init__(*args, **keywords)

    def quit(self, *args, **kwargs):
        """ Overridden to switch back to MAIN form """
        self.parentApp.switchForm('MAIN')

    def create(self):
        """ Update with current tools """
        self.add_handlers({"^T": self.quit, "^Q": self.quit})
        self.add(npyscreen.TitleText,
                 name='Select which tools to ' + self.action['action'] + ':',
                 editable=False)

        i = 4
        if self.action['action_name'] == 'start':
            response = self.action['api_action'].inventory(choices=['repos',
                                                                    'tools',
                                                                    'built',
                                                                    'enabled',
                                                                    'running',
                                                                    'core'])
        else:
            response = self.action['api_action'].inventory(choices=['core',
                                                                    'repos',
                                                                    'tools'])
        if response[0]:
            inventory = response[1]

            # TODO refactor this
            repos = inventory['repos']
            for repo in repos:
                if (self.action['cores'] or
                   (not self.action['cores'] and
                   repo != 'https://github.com/cyberreboot/vent')):
                    repo_name = repo.rsplit("/", 2)[1:]
                    if len(repo_name) == 1:
                        repo_name = repo.split('/')
                    self.tools_tc[repo] = {}
                    self.add(npyscreen.TitleText,
                             name='Plugin: '+repo,
                             editable=False, rely=i, relx=5)
                    i += 1
                    for tool in inventory['tools']:
                        r_name = tool[0].split(":")
                        if (repo_name[0] == r_name[0] and
                           repo_name[1] == r_name[1]):
                            core = False
                            if self.action['action_name'] == 'start':
                                running = False
                                built = False
                                enabled = False
                                for item in inventory['running']:
                                    if (tool[0] == item[0] and
                                       item[2] == 'running'):
                                        running = True
                                for item in inventory['built']:
                                    if tool[0] == item[0] and item[2] == 'yes':
                                        built = True
                                for item in inventory['enabled']:
                                    if tool[0] == item[0] and item[2] == 'yes':
                                        enabled = True
                            for item in inventory['core']:
                                if tool[0] == item[0]:
                                    core = True
                            t = tool[1]
                            if t == "":
                                t = "/"
                            if ((core and self.action['cores']) or
                               (not core and not self.action['cores'])):
                                if ((self.action['action_name'] == 'start' and
                                   not running and built and enabled) or
                                   self.action['action_name'] != 'start'):
                                    t += ":" + ":".join(tool[0].split(":")[-2:])
                                    self.tools_tc[repo][t] = self.add(npyscreen.CheckBox, name=t, value=True, relx=10)
                                    i += 1
                    i += 2
        return

    def on_ok(self):
        """
        Take the tool selections and perform the provided action on them
        """
        def diff(first, second):
            """
            Get the elements that exist in the first list and not in the second
            """
            second = set(second)
            return [item for item in first if item not in second]

        def popup(original, orig_type, thr, title):
            """
            Start the thread and display a popup of info
            until the thread is finished
            """
            thr.start()
            info_str = ""
            while thr.is_alive():
                if orig_type == 'containers':
                    info = diff(Containers(), original)
                elif orig_type == 'images':
                    info = diff(Images(), original)
                if info:
                    info_str = ""
                for entry in info:
                    info_str = entry[0] + ": " + entry[1] + "\n" + info_str
                if self.action['action_name'] != 'configure':
                    npyscreen.notify_wait(info_str, title=title)
                    time.sleep(1)
            return

        if self.action['type'] == 'images':
            originals = Images()
        else:
            originals = Containers()

        tool_d = {}
        if self.action['action_name'] in ['clean', 'remove', 'stop', 'update']:
            reconfirmation_str = ""
            if self.action['cores']:
                reconfirmation_str = "Are you sure you want to "
                reconfirmation_str += self.action['action_name']
                reconfirmation_str += " core containers?"
            else:
                reconfirmation_str = "Are you sure you want to "
                reconfirmation_str += self.action['action_name']
                reconfirmation_str += " plugin containers?"

            perform = npyscreen.notify_ok_cancel(reconfirmation_str,
                                                 title="Confirm command")
            if not perform:
                return
        for repo in self.tools_tc:
            for tool in self.tools_tc[repo]:
                self.logger.info(tool)
                if self.tools_tc[repo][tool].value:
                    t = tool
                    if t.startswith('/:'):
                        t = " "+t[1:]
                    t = t.split(":")
                    if self.action['action_name'] == 'start':
                        status = self.action['action_object2'](name=t[0],
                                                               branch=t[1],
                                                               version=t[2])
                        if status[0]:
                            tool_d.update(status[1])
                    else:
                        kargs = {'name': t[0],
                                 'branch': t[1],
                                 'version': t[2]}
                        # add core recognition
                        if self.action['cores']:
                            kargs.update({'groups': 'core'})
                        thr = Thread(target=self.action['action_object1'],
                                     args=(),
                                     kwargs=kargs)
                        popup(originals, self.action['type'], thr,
                              'Please wait, ' + self.action['present_t'] +
                              '...')
        if self.action['action_name'] == 'start':
            thr = Thread(target=self.action['action_object1'],
                         args=(),
                         kwargs={'tool_d': tool_d})
            popup(originals, self.action['type'], thr,
                  'Please wait, ' + self.action['present_t'] + '...')

        npyscreen.notify_confirm('Done ' + self.action['present_t'] + '.',
                                 title=self.action['past_t'])
        self.quit()

    def on_cancel(self):
        """ When user clicks cancel, will return to MAIN """
        self.quit()
