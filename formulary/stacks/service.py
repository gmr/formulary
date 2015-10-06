"""
Create the template for a Service stack

Service stacks include instances, auto-scaling groups, elastic load-balancers,
and Route53 DNS entries.

"""
import logging
from os import path

import troposphere
from troposphere import ec2

from formulary.stacks import base
from formulary import utils

LOGGER = logging.getLogger(__name__)

DEFAULT_DESCRIPTION = 'Formulary created service'


class Service(base.Stack):

    def __init__(self, config, name, vpc):
        """A service encapsulates the security groups, elastic-load-balancers,
        autoscaling groups or instances that constitute an application.

        """
        super(Service, self).__init__(config, name, vpc)
        self._template.description = config.settings.get('description',
                                                         DEFAULT_DESCRIPTION)
        self._add_security_groups()

    def _add_security_groups(self):

        if not self._config.settings.get('security-groups'):
            LOGGER.debug('No security groups defined')

        name = '{}-security-group'.format(self.name)
        security_group = ec2.SecurityGroup(name)
        security_group.Description = \
            'Security group for the {} service'.format(self.name)


        if 'ingress' in self._config.settings['security-groups']:
            security_group.Ingress = []
            for row in self._config.settings['security-groups']:
                pass




    def _add_security_group_ingress(self, config):

        name = '{}-ingress'.format(self.name)

        ingress = ec2.SecurityGroupIngress(name)


        pass




        pass


