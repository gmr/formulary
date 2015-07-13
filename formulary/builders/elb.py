"""
Build Cloud Formation ELB stacks

"""
from formulary.builders import base
from formulary.resources import elb

DEFAULT_PORT = 80
DEFAULT_PROTOCOL = 'http'


class LoadBalancer(base.Builder):
    """Build ELB Load Balancer stack"""
    def __init__(self, config, name, service, elb_config, instance_ids,
                 security_group, subnets):
        """Create an Elastic Load Balancer stack

        :param formulary.builders.config.Config: builder configuration
        :param str name: The base name fo the ELB stack
        :param dict elb_config: ELB specific configuration
        :param list instance_ids: List of reference IDs for the instances
        :param str security_group: The reference ID for the security group
        :param list subnets: List of subnet ids

        """
        name = '{0}-{1}'.format(config.environment, name)
        super(LoadBalancer, self).__init__(config, name)
        internal = elb_config.get('internal')
        self._add_resource(self.name,
                           elb.LoadBalancer(self.name,
                                            [{'Ref': i} for i in instance_ids],
                                            self._health_check(elb_config),
                                            self._listeners(elb_config),
                                            [{'Ref': security_group}], subnets,
                                            cross_zone=True,
                                            internal=internal))
        self._add_output('DNSName',
                         'The DNSName for {0}'.format(self.full_name),
                         {'Fn::GetAtt': [self.reference_id, 'DNSName']})
        self._add_output('HostedZoneId',
                         'The HostedZoneId for {0}'.format(self.full_name),
                         {'Fn::GetAtt': [self.reference_id,
                                         'CanonicalHostedZoneNameID']})
        self._add_tag_to_resources('Environment', config.environment)
        self._add_tag_to_resources('Service', service)

    @staticmethod
    def _create_listener(config):
        port = config.get('port', DEFAULT_PORT)
        protocol = config.get('protocol', DEFAULT_PROTOCOL)
        instance_port = config.get('instance_port', port)
        instance_protocol = config.get('instance_protocol', protocol)
        kwargs = {'port': port,
                  'protocol': protocol,
                  'instance_port': instance_port,
                  'instance_protocol': instance_protocol,
                  'ssl_certificate_id': config.get('ssl_certificate_id')}
        for key, value in [(k, v) for k, v in kwargs.items()]:
            if value is None:
                del kwargs[key]
        return elb.Listener(**kwargs)

    @staticmethod
    def _health_check(config):
        protocol = config.get('instance_protocol',
                              config.get('protocol', DEFAULT_PROTOCOL))
        port = config.get('instance_port', config.get('port', DEFAULT_PORT))
        kwargs = {'interval': config.get('interval'),
                  'target': '{0}:{1}{2}'.format(protocol.upper(), port,
                                                config.get('check', '')),
                  'timeout': config.get('timeout'),
                  'healthy': config.get('healthy'),
                  'unhealthy': config.get('unhealthy')}
        for key, value in [(k, v) for k, v in kwargs.items()]:
            if value is None:
                del kwargs[key]
        return elb.HeathCheck(**kwargs)

    def _listeners(self, config):
        values = []
        if config.get('listeners'):
            for listener in config['listeners']:
                values.append(self._create_listener(listener))
        else:
            values.append(self._create_listener(config))
        return values
