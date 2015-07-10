"""
Build the resources for a RDS Instance

"""
from formulary.builders import base
from formulary.builders import ec2
from formulary.resources import rds
from formulary import utils

DEFAULT_BACKUP_RETENTION = 3
DEFAULT_INSTANCE_TYPE = 'db.t2.small'
DEFAULT_ENGINE_TYPE = 'postgres'
DEFAULT_ENGINE_VERSION = '9.4.1'
DEFAULT_ENGINE_PORT = 5432
DEFAULT_STORAGE_CAPACITY = 100
DEFAULT_IOPS = 1000


class RDS(base.Builder):

    def __init__(self, config, name, stack):
        super(RDS, self).__init__(config, name)
        self._stack = stack
        self._security_group = self._add_security_group()
        self._add_instance()

    def _add_instance(self):
        subnets = self._add_subnet_groups()
        if not self._config.settings.get('multi-az'):
            self._config.settings['availability_zone'] = \
                self._stack.subnets[0].availability_zone
        name = '{0}-{1}'.format(self._config.environment, self._name)
        resource = rds.DBInstance(name,
                                  self._config.settings,
                                  utils.camel_case(subnets),
                                  {'Ref': self._security_group})
        resource.add_tag('Environment', self._stack.environment)
        resource.add_tag('Service', self._name)
        self._add_resource(name, resource)

    def _add_security_group(self):
        name = '{0}-security-group'.format(self._name)
        builder = ec2.SecurityGroup(self._config, name, self._stack,
                                    self._name)
        self._resources += builder.resources
        return builder.reference_id

    def _add_subnet_groups(self):
        subnets = []
        for subnet in self._stack.subnets:
            subnets.append(subnet.id)
        name = '{0}-{1}-subnet-group'.format(self._config.environment,
                                             self._name)
        resource = rds.DBSubnetGroup(name, subnets)
        self._add_resource(name, resource)
        return name
