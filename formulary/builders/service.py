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
from formulary.builders import route53
from formulary import utils

LOGGER = logging.getLogger(__name__)

# Defaults
DEFAULT_BLOCK_DEVICE = {'ebs': True, 'capacity': 20, 'type': 'gp2'}
DEFAULT_BLOCK_DEVICES = {'/dev/xvda': DEFAULT_BLOCK_DEVICE}


class Service(base.Builder):

    def __init__(self, config, name, amis, local_path, environment_stack,
                 dependency=None, wait_handle=None, parent=None,
                 users=None):
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
        self._users = users

        self._security_group = self._add_security_group()
        self._maybe_add_security_group_ingress()
        self._add_instances()
        self._maybe_add_elbs()
        self._maybe_add_route53_record_sets()
        self._add_tag_to_resources('Environment', self._config.environment)
        self._add_tag_to_resources('Service', self._name)

    def _add_autobalanced_instances(self, settings):
        count = settings.get('instance-count', 1)
        subnets = self._get_subnets(count)
        handle, wait = None, None
        for index in range(0, count):
            subnet = subnets.pop(0)
            if not handle:
                handle = self._maybe_add_wait_handle(index)
            ref_id = self._add_instance('instance{0}'.format(index), subnet,
                                        settings, handle, wait)
            if not wait:
                wait = self._maybe_add_wait_condition(index, handle, ref_id)

    # Add same-az instances in a method matching auto-balanced ones

    def _add_elb(self, name, config):
        if self._parent:
            name = '{0}-{1}'.format(self._parent, name)
        if '-' not in name:
            name = '{0}-{1}'.format(self._config.service, name)
        builder = elb.LoadBalancer(self._config, name, self.name, config,
                                   self._instances, 'SecurityGroupId',
                                   self.subnet_ids)
        builder.add_parameter('SecurityGroupId', {'Type': 'String'})
        parameters = {'SecurityGroupId':
                          {'Fn::GetAtt': [self._security_group,
                                          'Outputs.SecurityGroupId']}}

        for instance in self._instances:
            builder.add_parameter(instance, {'Type': 'String'})
            parameters[instance] = {'Fn::GetAtt': [instance,
                                                   'Outputs.InstanceId']}

        template_id, url = builder.upload(self._name)
        self._add_stack(name, url, parameters)
        self._maybe_add_route53_alias(config, utils.camel_case(name))

    def _add_instance(self, name, subnet, config,
                      wait_handle=None, dependency=None):
        """Add an instance to the resources for the given name, subnet, and
        config.

        :param str name: The name of the instance
        :param formulary.records.Subnet subnet: The subnet config
        :param dict config: The instance config
        :rtype: str

        """
        if self._parent:
            name = '{0}-{1}'.format(self._parent, name)
        LOGGER.debug('Adding %s', name)
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
                                config.get('ebs', True),
                                self._parent or self._environment_stack.name,
                                metadata=self._get_render_metadata())

        instance.add_parameter('SecurityGroupId',
                               {'Type': 'String',
                                'Description': 'Security Group Physical ID'})

        parameters = {'SecurityGroupId':
                          {'Fn::GetAtt': [self._security_group,
                                          'Outputs.SecurityGroupId']}}

        wait_handle = wait_handle or self._wait_handle
        if wait_handle:
            instance.add_parameter(wait_handle, {'Type': 'String'})
            parameters[wait_handle] = {'Ref': wait_handle}

        # Add any SecurityGroupIngress resources for public-ingress support
        for port in config.get('public-ingress', []):
            protocol, from_port, to_port = utils.parse_port_value(port)
            cidr = {'Fn::Join': ['',
                                 [{'Fn::GetAtt': [utils.camel_case(name),
                                                  'PublicIp']}, '/32']]}
            resource = \
                ec2_resources.SecurityGroupIngress({'Ref': 'SecurityGroupId'},
                                                   protocol, from_port, to_port,
                                                   cidr)
            instance.add_resource('{0}-{1}-{2}'.format(self._name, protocol,
                                                       to_port), resource)

        template_id, url = instance.upload(self._name)

        dependency = dependency or config.get('dependency') or self._dependency
        self._add_stack(name, url, parameters, dependency=dependency)
        ref_id = utils.camel_case(name)
        self._instances.append(ref_id)
        return ref_id

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
                self._add_instance('instance{0}'.format(index),
                                   subnet, settings)
        elif settings.get('instance-strategy') == 'az-balanced':
            return self._add_autobalanced_instances(settings)
        elif 'instance-strategy' in settings:
            raise ValueError('Unknown instance-strategy: '
                             '{0}'.format(settings['instance-strategy']))

    def _add_security_group(self):
        LOGGER.debug('Adding security group')
        name = '{0}-security-group'.format(self._config.service)
        if self._parent:
            name = '{0}-security-group'.format(self._parent)
        builder = ec2.SecurityGroup(self._config, name,
                                    self._environment_stack, self._name)
        template_id, url = builder.upload(self._name)
        self._add_stack(name, url)
        return utils.camel_case(name)

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

    def _get_render_metadata(self):
        return {'count': str(self._config.settings.get('instance-count', 1))}

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

    def _maybe_add_elbs(self):
        if not self._config.settings.get('elb'):
            return
        if isinstance(self._config.settings['elb'], list):
            for config in self._config.settings['elb']:
                self._add_elb(config['name'], config)
        elif isinstance(self._config.settings['elb'], dict):
            self._add_elb('elb', self._config.settings['elb'])

    def _maybe_add_route53_alias(self, config, ref_name):
        if 'route53' not in config:
            return
        name = '{0}-route53'.format(utils.dash_delimited(ref_name))
        builder = route53.Route53RecordSet(self._config, name,
                                           config['route53'])
        template_id, url = builder.upload(self._name)

        params = {'DNSName': {'Fn::GetAtt': [ref_name, 'Outputs.DNSName']},
                  'HostedZoneId': {'Fn::GetAtt': [ref_name,
                                                  'Outputs.HostedZoneId']}}

        self._add_stack(name, url, params)

    def _maybe_add_route53_record_sets(self):
        if 'route53' not in self._config.settings:
            return
        config = self._config.settings['route53']
        if isinstance(config, dict):
            return self._maybe_add_route53_record_set(config)
        elif isinstance(config, list):
            for entry in config:
                self._maybe_add_route53_record_set(entry)

    def _maybe_add_route53_record_set(self, config):
        name = '{0}-route53'.format(utils.dash_delimited(config['hostname']))
        builder = route53.Route53RecordSet(self._config, name, config,
                                           self._instances)
        template_id, url = builder.upload(self._name)
        params = dict()
        for instance in self._instances:
            priv = 'Public' if config.get('pubic') else 'Private'
            if 'srv' in config:
                params[instance] = {'Fn::GetAtt':
                                        [instance,
                                         'Outputs.{0}DnsName'.format(priv)]}
            else:
                params[instance] = {'Fn::GetAtt':
                                        [instance,
                                         'Outputs.{0}IP'.format(priv)]}
        self._add_stack(name, url, params)

    def _maybe_add_security_group_ingress(self):
        LOGGER.debug('Possibly adding security group ingress rules')
        name = 'security-group-ingress'
        if self._parent:
            name = '{0}-{1}'.format(self._parent, name)
        builder = ec2.SecurityGroupIngress(self._config, name,
                                           self._environment_stack,
                                           self._name)
        parameters = {'SecurityGroupId':
                          {'Fn::GetAtt': [self._security_group,
                                          'Outputs.SecurityGroupId']}}
        if builder.resources:
            template_id, url = builder.upload(self._name)
            self._add_stack(name, url, parameters,
                            dependency=self._security_group)

    def _maybe_add_wait_condition(self, index, handle, ref_id):
        if 'wait-condition' not in self._config.settings:
            return
        settings = self._config.settings['wait-condition']
        if index == settings['after-node']:
            name = '{0}-wait'.format(self._name)
            if self._parent:
                name = '{0}-{1}'.format(self._parent, name)
            handle = {'Ref': handle}
            timeout = settings.get('timeout', 3600)
            wait = cloudformation.WaitCondition(1, handle, timeout)
            wait.set_dependency(ref_id)
            self._add_resource(name, wait)
            cc_name = utils.camel_case(name)
            self._add_output(cc_name + 'Data', 'WaitCondition return data',
                             {'Fn::GetAtt': [cc_name, 'Data']})
            return cc_name

    def _maybe_add_wait_handle(self, index):
        if 'wait-condition' not in self._config.settings:
            return
        settings = self._config.settings['wait-condition']
        if index == settings['after-node']:
            name = utils.dash_delimited(settings['handle']) or self._name
            if self._parent:
                name = '{0}-{1}'.format(self._parent, name)
            self._add_resource(name,
                               cloudformation.WaitConditionHandle())
            return utils.camel_case(name)

    def _read_user_data(self):
        if self._config.settings.get('user-data'):
            with open(path.join(self._local_path,
                                self._config.settings['user-data'])) as handle:
                content = handle.read()
            if self._config.settings.get('include-users'):
                content += self._users
            return content

    @property
    def subnet_ids(self):
        """Return a list of Subnet IDs for the VPC

        :rtype: list

        """
        return [s.id for s in self._environment_stack.subnets]
