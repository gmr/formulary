"""
Build the resources for a RDS Instance

"""
from formulary import base
from formulary import resources
from formulary.builders import securitygroup
from formulary import utils

DEFAULT_BACKUP_RETENTION = 3
DEFAULT_INSTANCE_TYPE = 'db.t2.small'
DEFAULT_ENGINE_TYPE = 'postgres'
DEFAULT_ENGINE_VERSION = '9.4.1'
DEFAULT_ENGINE_PORT = 5432
DEFAULT_STORAGE_CAPACITY = 100
DEFAULT_IOPS = 1000


class RDS(base.Builder):

    def __init__(self, config, name, environment, mappings, stack):
        super(RDS, self).__init__(config, name, environment, mappings)
        self._stack = stack
        self._security_group = self._add_security_group()
        self._add_instance()

    def _add_instance(self):
        subnets = self._add_subnet_groups(self._config)
        if not self._config.get('multi-az'):
            self._config['availability_zone'] = \
                self._stack.subnets[0].availability_zone
        name = '{0}-{1}'.format(self._environment, self._name)
        resource = resources.DBInstance(name, self._config,
                                        utils.camel_case(subnets),
                                        {'Ref': self._security_group})
        self._add_resource(name, resource)

    def _add_security_group(self):
        builder = securitygroup.SecurityGroup(self._config,
                                              self._name,
                                              self._environment,
                                              self._mappings,
                                              self._stack)
        self._resources.update(builder.resources)
        return utils.camel_case(builder.logical_id)

    def _add_subnet_groups(self, config):
        subnets = []
        if config.get('multi-az'):
            subnets.append(self._stack.subnets[0].id)
        else:
            for subnet in self._stack.subnets:
                subnets.append(subnet.id)
        subnet_group_name = '{0}-{1}-subnet-group'.format(self._environment,
                                                          self._name)
        resource = resources.DBSubnetGroup(subnet_group_name, subnets)
        self._add_resource(subnet_group_name, resource)
        return subnet_group_name
