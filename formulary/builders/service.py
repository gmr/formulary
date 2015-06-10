"""

"""
import base64
import math
from os import path
import random
import re

from formulary import base
from formulary import resources
from formulary.builders import securitygroup
from formulary import utils

DEFAULT_INSTANCE_TYPE = 't2.small'
USER_DATA_RE = re.compile(r'\{\^(?P<command>instance|map)\s(?P<key>[\w\.]+)\}')


class Service(base.Builder):

    def __init__(self, config, name, environment, mappings,
                 stack, region, amis, instances, local_path):
        super(Service, self).__init__(config, name, environment, mappings)
        self._amis = amis
        self._instances = instances
        self._local_path = local_path
        self._mappings = mappings
        self._mappings.update(stack.mappings)
        self._region = region
        self._stack = stack
        self._security_group = self._add_security_group()
        self._add_instances()
        self._maybe_add_elbs()
        self._add_tag_to_resources('Environment', self._stack.environment)
        self._add_tag_to_resources('Service', self._name)

    def _add_autobalanced_instances(self):
        count = self._config.get('instance-count', 1)
        subnets = self._get_subnets(count)
        for index in range(0, count):
            subnet = subnets.pop(0)
            self._add_instance('{0}{1}'.format(self._name, index),
                               subnet, self._config)

    def _add_elb(self, name, config):
        protocol = config.get('protocol', 'http')
        instance_port = config.get('instance_port', config['port'])
        kwargs = {
            'port': config['port'],
            'protocol': protocol,
            'instance_port': instance_port,
            'instance_protocol': config.get('instance_protocol', protocol)
        }
        listeners = [resources.ELBListener(**kwargs)]

        kwargs = {'interval': config.get('interval'),
                  'target': '{0}:{1}{2}'.format(protocol.upper(), instance_port,
                                                config.get('check', '')),
                  'timeout': config.get('timeout'),
                  'healthy': config.get('healthy'),
                  'unhealthy': config.get('unhealthy')}
        for key, value in [(k, v) for k, v in kwargs.items()]:
            if value is None:
                del kwargs[key]
        health_check = resources.ELBHeathCheck(**kwargs)

        instances = [{'Ref': i} for i in self._instance_ids]

        self._add_resource(name,
                           resources.ELB(name, instances,
                                         health_check, listeners,
                                         [{'Ref': self._security_group}],
                                         self._instance_subnets))

    def _add_instance(self, name, subnet, config):
        """Add an instance to the resources for the given name, subnet, and
        config.

        :param str name: The name of the instance
        :param formulary.records.Subnet subnet: The subnet config
        :param dict config: The instance config
        :rtype: str

        """
        kwargs = {
            'name': '{0}-service-{1}'.format(self._environment, name),
            'ami': self._get_ami_id(),
            'availability_zone': subnet.availability_zone,
            'instance_type': config.get('instance-type'),
            'environment': self._environment,
            'region': self._region,
            'subnet': subnet.id,
            'security_group': {'Ref': self._security_group},
            'service': self._name,
            'storage_size': config.get('storage-capacity'),
            'private_ip': config.get('private_ip', '')
        }
        kwargs['user_data'] = self._get_user_data(config.get('user-data'),
                                                  kwargs)
        for key in ['environment', 'region', 'service']:
            del kwargs[key]
        resource = resources.EC2Instance(**kwargs)
        return self._add_resource(name, resource)

    def _add_instances(self):
        if 'instances' in self._config:
            for name, instance_cfg in self._config['instances'].items():
                cfg = dict(self._config)
                del cfg['instances']
                cfg.update(instance_cfg)
                for key in ['availability_zone', 'private_ip']:
                    cfg[key] = self._maybe_replace_with_mapping(cfg[key])
                self._maybe_add_availability_zone(cfg)
                self._add_instance('{0}-{1}'.format(self._environment, name),
                                   self._get_subnet(cfg['availability_zone']),
                                   cfg)
        elif self._config.get('instance-strategy') == 'same-az':
            self._maybe_add_availability_zone(self._config)
            subnet = self._get_subnet(self._config['availability_zone'])
            for index in range(0, self._config.get('instance-count', 1)):
                self._add_instance('{0}-{1}{2}'.format(self._environment,
                                                       self._name, index),
                                   subnet, self._config)
        elif self._config.get('instance-strategy') == 'az-balanced':
            return self._add_autobalanced_instances()
        elif 'instance-strategy' in self._config:
            raise ValueError('Unknown instance-strategy: '
                             '{0}'.format(self._config['instance-strategy']))

    def _add_security_group(self):
        builder = securitygroup.SecurityGroup(self._config,
                                              self._name,
                                              self._environment,
                                              self._mappings,
                                              self._stack)
        self._resources.update(builder.resources)
        return utils.camel_case(builder.logical_id)

    def _add_tag_to_resources(self, tag, value):
        for name, resource in self._resources.items():
            resource.add_tag(tag, value)

    def _get_ami_id(self):
        try:
            return self._amis[self._region][self._config.get('ami')]
        except KeyError:
            raise ValueError('AMI "%s" not found' % self._config.get('ami'))

    def _get_subnet(self, availability_zone):
        for subnet in self._get_subnets(len(self._stack.subnets)):
            if subnet.availability_zone == availability_zone:
                return subnet

    def _get_subnets(self, count):
        subnets = self._stack.subnets
        if count > len(subnets):
            subnets *= math.ceil(count / float(len(subnets)))
        return subnets[0:count]

    def _get_user_data(self, filename, kwargs):
        if filename:
            with open(path.join(self._local_path, filename), 'r') as handle:
                return self._render_user_data(handle.read(), kwargs)
        return None

    @property
    def _instance_ids(self):
        ids = []
        for k, v in self._resources.items():
            if isinstance(v, resources.EC2Instance):
                ids.append(k)
        return ids

    @property
    def _instance_subnets(self):
        return [v.subnet for v in self._resources.values()
                if isinstance(v, resources.EC2Instance)]

    def _maybe_add_availability_zone(self, config):
        if 'availability_zone' not in config:
            offset = random.randint(0, len(self._stack.subnets) - 1)
            config['availability_zone'] = \
                self._stack.subnets[offset].availability_zone

    def _maybe_add_elbs(self):
        for name, config in self._config.get('elb', {}).items():
            self._add_elb('{0}-{1}'.format(self._environment, name), config)

    def _render_user_data(self, content, kwargs):
        mappings = dict(self._mappings)
        for match in USER_DATA_RE.finditer(content):
            if match.group(1) == 'map':
                value = mappings
                for key in str(match.group(2)).split('.'):
                    value = value.get(key.strip())
                content = content.replace(match.group(0), value)
            elif match.group(1) == 'instance':
                content = content.replace(match.group(0),
                                          kwargs[match.group(2)])
        return base64.b64encode(content.encode('utf-8')).decode('utf-8')
