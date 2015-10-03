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

    def __init__(self, cfg, name, vpc):
        """

        """
        super(Service, self).__init__(cfg, name, vpc)

