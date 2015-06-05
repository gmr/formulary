"""
Interfaces for building a service stack

"""
import base64
import logging
import math
from os import path
import re

from formulary import cloudformation
from formulary import security_group

LOGGER = logging.getLogger(__name__)

DEFAULT_INSTANCE_TYPE = 't2.small'
USER_DATA_RE = re.compile(r'\{\^(?P<command>instance|map)\s(?P<key>[\w\.]+)\}')


class ServiceTemplate(security_group.TemplateWithSecurityGroup):

    CONFIG_PREFIX = 'services'
    PARENT_CONFIG_PREFIX = 'vpcs'
    STACK_TYPE = 'Service'

    def __init__(self, name, parent, config_path, region='us-east-1'):
        super(ServiceTemplate, self).__init__(name, parent, config_path, region)
        self._config = self._load_config(self._local_path, 'service')
        if self._config.get('description'):
            self._description = self._config['description']
        self._init_network_stack()
        self._security_group = self._add_security_group()
        self._add_instances()

    def _add_autobalanced_instances(self, config):
        count = config.get('instance-count', 1)
        subnets = self._get_subnets(count)
        for index in range(0, count):
            subnet = subnets.pop(0)
            kwargs = {
                'name': '{0}{1}'.format(self.name, index),
                'ami': self._get_ami_id(),
                'availability_zone': subnet.availability_zone,
                'instance_type': config.get('instance-type'),
                'subnet': subnet.id,
                'service': self._name,
                'sec_group': self._security_group,
                'storage_size': config.get('storage-capacity')
            }
            kwargs['user_data'] = self._get_user_data(config.get('user-data'),
                                                      kwargs)
            del kwargs['service']
            resource = _EC2Instance(**kwargs)
            self._add_environment_tag(resource)
            self.add_resource('{0}{1}'.format(self._to_camel_case(self._name),
                                              index), resource)

    def _add_instance(self, name, config, instance_cfg):
        availability_zone = \
            self._mapping_replace(instance_cfg.get('availability_zone'))
        subnet_id = instance_cfg.get('subnet')
        private_ip = self._mapping_replace(instance_cfg.get('private_ip'))

        if subnet_id and not availability_zone:
            for subnet in self._network_stack.subnets:
                if subnet.id == subnet_id:
                    availability_zone = subnet.availability_zone

        elif availability_zone and not subnet_id:
            for subnet in self._network_stack.subnets:
                if subnet.availability_zone == availability_zone:
                    subnet_id = subnet.id
                    break

        kwargs = {
            'name': '{0}-{1}'.format(self.name, name.lower()),
            'ami': self._get_ami_id(),
            'availability_zone': availability_zone,
            'instance_type': config.get('instance-type'),
            'subnet': subnet_id,
            'sec_group': self._security_group,
            'service': self._name,
            'storage_size': config.get('storage-capacity'),
            'private_ip': private_ip
        }
        del kwargs['service']
        kwargs['user_data'] = self._get_user_data(config.get('user-data'),
                                                  kwargs)
        resource = _EC2Instance(**kwargs)
        self._add_environment_tag(resource)
        self.add_resource('{0}{1}'.format(self._to_camel_case(self._name),
                                          name), resource)

    def _add_instances(self):
        config = self._flatten_config(self._config)
        if config.get('instance-strategy') == 'az-balanced':
            return self._add_autobalanced_instances(config)

        for name, instance_cfg in config.get('instances', {}).items():
            self._add_instance(name, config, instance_cfg)

    def _get_ami_id(self):
        amis = self._load_config(self._config_path, 'amis')
        try:
            return amis[self._region][self._config.get('ami')]
        except KeyError:
            raise ValueError('AMI "%s" not found' % self._config.get('ami'))

    def _get_subnets(self, count):
        subnets = self._network_stack.subnets
        if count > len(subnets):
            subnets *= math.ceil(count / float(len(subnets)))
        return subnets[0:count]

    def _get_user_data(self, filename, kwargs):
        if filename:
            with open(path.join(self._local_path, filename), 'r') as handle:
                return self._render_user_data(handle.read(), kwargs)
        return None

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


class _EC2Instance(cloudformation.Resource):
    def __init__(self, name, ami, availability_zone, instance_type, subnet,
                 sec_group, user_data,
                 storage_size=20,
                 private_ip=None):
        super(_EC2Instance, self).__init__('AWS::EC2::Instance')
        self._name = name
        nic = {
            'AssociatePublicIpAddress': True,
            'DeviceIndex': '0',
            'GroupSet': [sec_group],
            'SubnetId': subnet
        }
        if private_ip:
            nic['PrivateIpAddress'] = private_ip
        volume = {
            'DeviceName': '/dev/xvda',
            'Ebs': {'VolumeType': 'gp2',
                    'VolumeSize': storage_size}
        }
        self._properties = {
            'AvailabilityZone': availability_zone,
            'BlockDeviceMappings': [volume],
            'DisableApiTermination': False,
            'EbsOptimized': False,
            'ImageId': ami,
            'InstanceInitiatedShutdownBehavior': 'stop',
            'InstanceType': (instance_type or DEFAULT_INSTANCE_TYPE),
            'KeyName': {'Fn::FindInMap': ['AWS', 'KeyName', 'Value']},
            'Monitoring': False,
            'NetworkInterfaces': [nic],
            'UserData': user_data
        }
        self._prune_empty_properties()
