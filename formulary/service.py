"""
Interfaces for building a service stack

"""
import base64
import logging
import math
from os import path
import re

from formulary import cloudformation
from formulary import network

LOGGER = logging.getLogger(__name__)

DEFAULT_INSTANCE_TYPE = 't2.small'
USER_DATA_RE = re.compile(r'\{\^(?P<command>instance|map)\s(?P<key>[\w\.]+)\}')


class ServiceStackTemplate(cloudformation.Template):

    CONFIG_PREFIX = 'services'
    PARENT_CONFIG_PREFIX = 'vpcs'

    def __init__(self, name, parent, region, config_path):
        super(ServiceStackTemplate, self).__init__(name, parent, config_path)
        self._config = self._load_config(self._local_path, 'service')
        self.parent = parent
        self._region = region
        self._network_stack = network.NetworkStack(parent, config_path, region)
        self._add_network_mappings()

        if isinstance(self._config.get('security-group'), str):
            self._security_group = self._config.get('security-group')
        else:
            self._security_group = self._add_security_group()
        if self._config.get('description'):
            self._description = self._config['description']
        self._add_instances()

    def _add_autobalanced_instances(self):
        count = self._config.get('instance-count', 1)
        subnets = self._get_subnets(count)
        for index in range(0, count):
            subnet = subnets.pop(0)
            kwargs = {
                'name': '{0}{1}'.format(self.name, index),
                'ami': self._get_ami_id(),
                'availability_zone': subnet.availability_zone,
                'instance_type': self._config.get('instance-type'),
                'subnet': subnet.id,
                'security_group': self._security_group,
                'storage_size': self._config.get('storage-capacity')
            }
            kwargs['user_data'] = \
                self._get_user_data(self._config.get('user-data'), kwargs)
            resource = _EC2Instance(**kwargs)
            self._add_environment_tag(resource)
            self.add_resource('{0}{1}'.format(self._name.capitalize(), index),
                              resource)

    def _add_environment_tag(self, resource):
        resource.add_tag('Environment', self._network_stack.environment)

    def _add_network_mappings(self):
        vpc = dict()
        for key, value in self._network_stack.vpc._asdict().items():
            cckey = ''.join(x.capitalize() for x in key.split('_'))
            if key == 'cidr_block':
                cckey = 'CIDR'
            vpc[cckey] = value
        mappings = {
            'Network': {
                'Name': {'Value': self._network_stack.name},
                'VPC': vpc,
                'AWS': {'Region': self._region}
            }
        }
        self.update_mappings(mappings)

    def _add_instances(self):
        if self._config.get('instance-strategy') == 'az-balanced':
            return self._add_autobalanced_instances()

        for name, config in self._config.get('instances', {}).items():
            self._add_instance(name, config)

    def _add_instance(self, name, config):
        availability_zone = \
            self._mapping_replace(config.get('availability_zone'))
        subnet_id = config.get('subnet')
        private_ip = self._mapping_replace(config.get('private_ip'))

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
            'instance_type': self._config.get('instance-type'),
            'subnet': subnet_id,
            'security_group': self._security_group,
            'storage_size': self._config.get('storage-capacity'),
            'private_ip': private_ip
        }
        kwargs['user_data'] = self._get_user_data(self._config.get('user-data'),
                                                  kwargs)
        resource = _EC2Instance(**kwargs)
        self._add_environment_tag(resource)
        self.add_resource('{0}{1}'.format(self._name.capitalize(), name),
                          resource)

    def _add_security_group(self):
        environment = self._network_stack.environment
        desc = ('Security Group for the {0} '
                'service in {1}').format(self._name.capitalize(),
                                         environment.capitalize())
        resource = _SecurityGroup('{0}-service'.format(self.name), desc,
                                  self._network_stack.vpc.id,
                                  self._build_ingress_rules())
        self._add_environment_tag(resource)
        name = '{0}{1}ServiceSecurityGroup'.format(environment.capitalize(),
                                                   self._name.capitalize())
        self.add_resource(name, resource)
        return name

    def _build_ingress_rules(self):
        rules = []
        group = self._config.get('security-group', {})
        ingress_rules = list(group.get('ingress', {}))
        for row in ingress_rules:
            try:
                port, source = dict(row).popitem()
            except KeyError:
                continue
            protocol, from_port, to_port = self._get_protocol_and_ports(port)
            cidr_block = self._find_in_map(source)
            rules.append(_SecurityGroupRule(protocol, from_port, to_port,
                                            cidr_block).as_dict())
        return rules

    def _get_ami_id(self):
        amis = self._load_config(self._config_path, 'amis')
        try:
            return amis[self._region][self._config.get('ami')]
        except KeyError:
            raise ValueError('AMI "%s" not found' % self._config.get('ami'))

    @staticmethod
    def _find_in_map(source):
        if source.startswith('^map '):
            ref = source[5:].split('.')
            return {'Fn::FindInMap': ref}
        return source

    @staticmethod
    def _get_protocol_and_ports(port):
        protocol = 'tcp'
        if isinstance(port, int):
            return protocol, port, port
        if '/' in port:
            port, protocol = port.split('/')
        if '-' in port:
            from_port, to_port = port.split('-')
        else:
            from_port, to_port = port, port
        return protocol, from_port, to_port

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

    def _mapping_replace(self, source):
        if source.startswith('^map '):
            value = dict(self._mappings)
            for key in source[5:].split('.'):
                value = value[key.strip()]
            return value
        return source

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
                 security_group, user_data,
                 storage_size=20,
                 private_ip=None):
        super(_EC2Instance, self).__init__('AWS::EC2::Instance')
        self._name = name
        nic = {
            'AssociatePublicIpAddress': True,
            'DeviceIndex': '0',
            'GroupSet': [{'Ref': security_group}],
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
        for key, value in list(self._properties.items()):
            if self._properties[key] is None:
                LOGGER.info('Removing empty key for %s', key)
                del self._properties[key]


class _SecurityGroup(cloudformation.Resource):
    def __init__(self, name, description, vpc, ingress):
        super(_SecurityGroup, self).__init__('AWS::EC2::SecurityGroup')
        self._name = name
        self._properties['GroupDescription'] = description
        self._properties['SecurityGroupIngress'] = ingress
        self._properties['VpcId'] = vpc


class _SecurityGroupRule(object):
    def __init__(self, protocol, from_port,
                 to_port=None,
                 cidr_addr=None,
                 source_id=None,
                 source_name=None,
                 source_owner=None):
        self._value = {
            'CidrIp': cidr_addr,
            'FromPort': from_port,
            'IpProtocol': protocol,
            'SourceSecurityGroupId': source_id,
            'SourceSecurityGroupName': source_name,
            'SourceSecurityGroupOwnerId': source_owner,
            'ToPort': to_port or from_port
        }

    def as_dict(self):
        value = dict(self._value)
        for key in self._value.keys():
            if value[key] is None:
                del value[key]
        return value
