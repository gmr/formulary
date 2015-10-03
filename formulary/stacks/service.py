"""
Create the template for a Service stack

Service stacks include instances, auto-scaling groups, elastic load-balancers,
and Route53 DNS entries.

"""
from os import path

import troposphere
from troposphere import ec2

from formulary.stacks import base
from formulary import config
from formulary import utils


class Service(base.Stack):

    def __init__(self, config, name, vpc):
        """
        cfg = config.Resource(config_path, 'service', name, vpc.name)

        self._mappings = cfg.load_file('')
        super(Service, self).__init__(cfg.load(), name, vpc.name)

        self._config_path = cfg.base_path
        self._users = []
        self._vpc_stack = vpc_stack

        """
        super(Service, self).__init__(config, name, vpc)


    def _read_user_data(self):
        if self._config.settings.get('user-data'):
            with open(path.join(self._config_path,
                                self._config.settings['user-data'])) as handle:
                content = handle.read()
            if self._config.settings.get('include-users'):
                content += self._users
            return content
