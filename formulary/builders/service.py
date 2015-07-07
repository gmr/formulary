"""

"""
import logging
import math
from os import path
import random

from formulary.builders import base

from formulary.resources import cloudformation
from formulary.builders import ec2
from formulary.resources import ec2 as ec2_resources
from formulary.builders import elb

from formulary.builders import securitygroup
from formulary import utils

LOGGER = logging.getLogger(__name__)

# Defaults
DEFAULT_BLOCK_DEVICE = {'ebs': True, 'capacity': 20, 'type': 'gp2'}
DEFAULT_BLOCK_DEVICES = {'/dev/xvda': DEFAULT_BLOCK_DEVICE}


class Service(base.Builder):

    def __init__(self, config, name, amis, local_path, environment_stack,
                 dependency=None, wait_handle=None, parent=None):
        super(Service, self).__init__(config, name)

        self._amis = amis
        self._instances = []
        self._local_path = local_path
        self._mappings = config.mappings
        self._mappings.update(environment_stack.mappings)
        self._dependency = dependency
        self._wait_handle = wait_handle
        self._environment_stack = environment_stack
        self._parent = parent
        self._security_group = self._add_security_group()
        self._add_instances()

        #self._maybe_add_elbs()
        #self._maybe_add_route53_resources(self._config)
        self._add_tag_to_resources('Environment', self._config.environment)
        self._add_tag_to_resources('Service', self._name)

    def _add_autobalanced_instances(self, settings):
        count = settings.get('instance-count', 1)
        subnets = self._get_subnets(count)
        for index in range(0, count):
            subnet = subnets.pop(0)
            self._add_instance('{0}{1}'.format(self._name, index),
                               subnet, settings)

    def _add_instance(self, name, subnet, config):
        """Add an instance to the resources for the given name, subnet, and
        config.

        :param str name: The name of the instance
        :param formulary.records.Subnet subnet: The subnet config
        :param dict config: The instance config
        :rtype: str

        """
        LOGGER.debug('Adding instance %s', name)
        block_devices = self._get_block_devices(config.get('block_devices'))
        instance = ec2.Instance(self._config, name,
                                self._get_ami_id(),
                                block_devices,
                                config.get('instance-type'),
                                config.get('private_ip', ''),
                                {'Ref': 'SecurityGroupId'},
                                subnet,
                                self._read_user_data(),
                                self._tags,
                                None,
                                config.get('ebs', True),
                                self._parent or self._environment_stack.name)

        instance.add_parameter('SecurityGroupId',
                               {'Type': 'String',
                                'Description': 'Security Group Physical ID'})
        parameters = {'SecurityGroupId':
                             {'Fn::GetAtt': [self._security_group,
                                             'Outputs.SecurityGroupId']}}

        """
        if dependency:
            instance.add_parameter(dependency,
                                   {'Type': 'String',
                                    'Description': 'Resource dependency'})
            parameters[dependency] = {'Ref': dependency}
        """

        if self._wait_handle:
            instance.add_parameter(self._wait_handle,
                                   {'Type': 'String',
                                    'Description': 'Resource wait handle'})
            parameters[self._wait_handle] = {'Ref': self._wait_handle}

        template_id, url = instance.upload(self._name)

        dependency = config.get('dependency') or self._dependency
        self._add_stack(name, url, parameters, dependency=dependency)

    def _add_instances(self):
        settings = self._config.settings
        if 'instances' in settings:
            LOGGER.debug('Adding instances')
            for name, instance_cfg in settings['instances'].items():
                cfg = dict(settings)
                del cfg['instances']
                cfg.update(instance_cfg)
                for key in ['availability_zone', 'private_ip']:
                    cfg[key] = self._maybe_replace_with_mapping(cfg[key])
                self._maybe_add_availability_zone(cfg)
                self._add_instance(name,
                                   self._get_subnet(cfg['availability_zone']),
                                   cfg)
        elif settings.get('instance-strategy') == 'same-az':
            self._maybe_add_availability_zone(settings)
            subnet = self._get_subnet(settings['availability_zone'])
            for index in range(0, settings.get('instance-count', 1)):
                self._add_instance('{1}{2}'.format(self._name, index),
                                   subnet, settings)
        elif settings.get('instance-strategy') == 'az-balanced':
            return self._add_autobalanced_instances(settings)
        elif 'instance-strategy' in settings:
            raise ValueError('Unknown instance-strategy: '
                             '{0}'.format(settings['instance-strategy']))

    def _add_security_group(self):
        builder = securitygroup.SecurityGroup(self._config,
                                              self._name,
                                              self._environment_stack)
        template_id, url = builder.upload(self.name)
        security_group_stack = '{0}-security-group-stack'.format(self._name)
        stack_name = utils.camel_case(security_group_stack)
        self._add_stack(security_group_stack, url)
        return stack_name

    def _add_tag_to_resources(self, tag, value):
        for (k, resource) in self._resources:
            resource.add_tag(tag, value)

    def _add_wait_condition(self, name):
        self._add_resource(name, cloudformation.WaitConditionHandle())

    def _get_ami_id(self):
        try:
            return self._amis[self._config.region][self._config.settings['ami']]
        except KeyError:
            raise ValueError('AMI %s not found' % self._config.settings['ami'])

    @staticmethod
    def _get_block_devices(devices):
        if devices == 'instance-store':
            return
        if not devices:
            devices = DEFAULT_BLOCK_DEVICES
        values = []
        for index, (device, config) in enumerate(devices.items()):
            kwargs = {'name': device}
            if config.get('ebs', DEFAULT_BLOCK_DEVICE['ebs']):
                kwargs['ebs'] = {
                    'VolumeType': config.get('type',
                                             DEFAULT_BLOCK_DEVICE['type']),
                    'VolumeSize': config.get('capacity',
                                             DEFAULT_BLOCK_DEVICE['capacity'])}
            else:
                kwargs['virtual_name'] = 'ephemeral{0}'.format(index)
            values.append(ec2_resources.BlockDevice(**kwargs).as_dict())

        LOGGER.debug('Block devices: %r', values)
        return values

    def _get_subnet(self, availability_zone):
        for subnet in self._get_subnets(len(self._environment_stack.subnets)):
            if subnet.availability_zone == availability_zone:
                return subnet

    def _get_subnets(self, count):
        subnets = self._environment_stack.subnets
        if count > len(subnets):
            subnets *= math.ceil(count / float(len(subnets)))
        return subnets[0:count]

    def _maybe_add_availability_zone(self, config):
        if 'availability_zone' not in config:
            offset = random.randint(0, len(self._environment_stack.subnets) - 1)
            config['availability_zone'] = \
                self._environment_stack.subnets[offset].availability_zone

    def _read_user_data(self):
        if self._config.settings.get('user-data'):
            with open(path.join(self._local_path,
                                self._config.settings['user-data'])) as handle:
                return handle.read()
