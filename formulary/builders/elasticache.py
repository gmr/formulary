"""
Build Cloud Formation ELB stacks

"""
from formulary.builders import base
from formulary.builders import ec2
from formulary.resources import elasticache
from formulary import utils

class Cache(base.Builder):
    """Build ELB Load Balancer stack"""
    def __init__(self, config, name, stack):
        """Create an Elastic Load Balancer stack

        :param formulary.builders.config.Config: builder configuration
        :param str name: The base name fo the ELB stack

        """
        name = '{0}-{1}'.format(config.environment, name)
        super(Cache, self).__init__(config, name)
        self._stack = stack
        self._security_group = self._add_security_group()
        self._add_instance()

    def _add_instance(self):
        subnet = utils.camel_case(self._add_subnet_groups())
        settings = self._config.settings
        if not settings.get('multi-az'):
            settings['availability_zone'] = \
                self._stack.subnets[0].availability_zone
        else:
            settings['preferred_azs'] = \
                [s.availability_zone for s in self._stack.subnets]

        kwargs = {'name': self._name,
                  'minor_version_upgrade': settings.get('minor-version-upgrade',
                                                        False),
                  'engine': settings.get('engine'),
                  'version': settings.get('engine-version'),
                  'node_qty': settings.get('instance-count', 1),
                  'node_type': settings.get('instance-type'),
                  'port': settings.get('port'),
                  'preferred_az': settings.get('availability_zone'),
                  'preferred_azs': settings.get('preferred_azs'),
                  'subnet_group_name': {'Ref': subnet},
                  'vpc_security_group_ids': [{'Ref': self._security_group}]}

        resource = elasticache.CacheCluster(**kwargs)
        resource.add_tag('Environment', self._stack.environment)
        resource.add_tag('Service', self._name)
        self._add_resource(kwargs['name'], resource)
        self._add_output('Address',
                         'The endpoint address for {0}'.format(self.full_name),
                         {'Fn::GetAtt': [self.reference_id,
                                         'ConfigurationEndpoint.Address']})
        self._add_output('Port',
                         'The endpoint port for {0}'.format(self.full_name),
                         {'Fn::GetAtt': [self.reference_id,
                                         'ConfigurationEndpoint.Port']})

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
        name = '{0}-subnet-group'.format(self._name)
        resource = elasticache.SubnetGroup(name, subnets)
        self._add_resource(name, resource)
        return name
