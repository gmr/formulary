"""
Build Cloud Formation EC2 stacks

"""
import json
import logging
import re

from formulary.builders import base
from formulary.resources import ec2
from formulary import s3
from formulary import utils

LOGGER = logging.getLogger(__name__)

DEFAULT_INSTANCE_TYPE = 't2.small'
USER_DATA_RE = re.compile(r'\{\^(?P<command>instance|map)\s(?P<key>[\w\.]+)\}')
USER_DATA_JSON = re.compile(r'(\{\"(?:Ref|Fn\::\w+)\"[\s\:]+'
                            r'(?:\".*?\"|\[.*?\])\})')


class Instance(base.Builder):

    def __init__(self, config, name, ami, block_devices, instance_type,
                 private_ip, security_group, subnet, user_data, tags,
                 ebs=True, stack_name=None, dependency=None, metadata=None):
        """Create a new EC2 instance builder

        :param formulary.builders.config.Config: builder configuration
        :param str name:
        :param str ami:
        :param list block_devices:
        :param str instance_type:
        :param str private_ip:
        :param str security_group:
        :param formulary.resources.ec2.Subnet subnet:
        :param str user_data:
        :param dict tags: Tags to add to the resource
        :param bool ebs: Is EBS backed
        :param str stack_name: The name of the parent stack for the instance

        """
        super(Instance, self).__init__(config, name)
        self._s3 = s3.S3(config.s3_bucket, config.s3_prefix, config.profile)

        # Build kwargs used for user-data template and ec2.Instance
        kwargs = {'name': self.full_name,
                  'ami': ami,
                  'availability_zone': subnet.availability_zone,
                  'block_devices': block_devices,
                  'dependency': dependency,
                  'environment': config.environment,
                  'instance_type': instance_type,
                  'private_ip': private_ip,
                  'ref_id': self.reference_id,
                  'region': config.region,
                  'service': config.service,
                  'subnet': subnet.id,
                  'security_group': security_group,
                  'stack': stack_name,
                  'ebs': ebs}

        if metadata:
            kwargs.update(metadata)

        kwargs['user_data'] = self._render_user_data(user_data, kwargs)

        if metadata:
            for key in metadata:
                del kwargs[key]

        # Remove the kwargs that don't get passed to ec2.Instance
        for key in ['environment', 'ref_id', 'region', 'service', 'stack']:
            del kwargs[key]

        resource = ec2.Instance(**kwargs)
        for key, value in tags.items():
            resource.add_tag(key, value)
        ref_id = self._add_resource(self.name, resource)

        # Add private and public IP output
        self._add_output('InstanceId',
                         'The logical ID for {0}'.format(self.full_name),
                         {'Ref': ref_id})
        self._add_output('PrivateIP',
                         'Private IP address for {0}'.format(self.full_name),
                         {'Fn::GetAtt': [ref_id, 'PrivateIp']})
        self._add_output('PublicIP',
                         'Public IP address for {0}'.format(self.full_name),
                         {'Fn::GetAtt': [ref_id, 'PublicIp']})
        self._add_output('PrivateDnsName',
                         'Private DNS for {0}'.format(self.full_name),
                         {'Fn::GetAtt': [ref_id, 'PrivateDnsName']})
        self._add_output('PublicDnsName',
                         'Public DNS for {0}'.format(self.full_name),
                         {'Fn::GetAtt': [ref_id, 'PublicDnsName']})

    def _render_user_data(self, content, kwargs):
        for match in USER_DATA_RE.finditer(content):
            if match.group(1) == 'map':
                value = self._config.mappings
                for key in str(match.group(2)).split('.'):
                    try:
                        value = value.get(key.strip())
                    except AttributeError:
                        LOGGER.warning('Error assigning user-data value '
                                       'to "%s", value does not exist', key)
                content = content.replace(match.group(0), value)
            elif match.group(1) == 'instance':
                content = content.replace(match.group(0),
                                          kwargs[match.group(2)])
            elif match.group(1) == 's3file':
                value = self._s3.fetch(str(match.group(2)))
                content = content.replace(match.group(0), value)

        data = []
        for line in content.split('\n'):
            matches = USER_DATA_JSON.findall(line)
            if not matches:
                data.append(line + '\n')
                continue

            parts = USER_DATA_JSON.split(line)
            for offset, part in enumerate(parts):
                if part in matches:
                    parts[offset] = json.loads(part)
            if isinstance(parts[-1], dict):
                parts.append('\n')
            else:
                parts[-1] += '\n'
            for part in parts:
                data.append(part)

        return {'Fn::Base64': {'Fn::Join': ['', data]}}



class SecurityGroup(base.Builder):

    def __init__(self, config, name, stack, owner):
        super(SecurityGroup, self).__init__(config, name)
        self._owner = owner
        self._name = name
        self._stack = stack
        self._add_security_group()
        self._add_output('SecurityGroupId',
                         'The physical ID for the security group',
                         {'Ref': self.reference_id})

        self._add_tag_to_resources('Environment', config.environment)
        self._add_tag_to_resources('Service', owner)

    def _add_security_group(self):
        if isinstance(self._config.settings.get('security-group'), str):
            return self._config.settings.get('security-group')

        desc = ('Security Group for the {0} '
                'service in {1}').format(self._owner.capitalize(),
                                         self._stack.environment.capitalize())
        resource = ec2.SecurityGroup(self._name, desc, self._stack.vpc.id,
                                     self._build_ingress_rules())
        self._add_resource(self._name, resource)

    def _build_ingress_rules(self):
        rules = []
        group = self._config.settings.get('security-group', {})
        ingress_rules = list(group.get('ingress', {}))
        for row in ingress_rules:
            try:
                port, source = dict(row).popitem()
            except KeyError:
                continue
            if source == 'security-group':
                continue
            protocol, from_port, to_port = utils.parse_port_value(port)
            cidr_block = utils.find_in_map(source)
            rules.append(ec2.SecurityGroupRule(protocol,
                                               from_port, to_port,
                                               cidr_block).as_dict())
        return rules


class SecurityGroupIngress(base.Builder):

    def __init__(self, config, name, stack, owner):
        super(SecurityGroupIngress, self).__init__(config, name)
        self._owner = owner
        self._name = name
        self._stack = stack
        self._add_parameter('SecurityGroupId', {'Type': 'String'})

        for port in self._get_ingress_ports():
            protocol, from_port, to_port = utils.parse_port_value(port)
            ref_id = {'Ref': 'SecurityGroupId'}
            resource = ec2.SecurityGroupIngress(ref_id, protocol, from_port,
                                                to_port, ref_id)
            name = '{0}-{1}-{2}'.format(self._name, protocol, to_port)
            self._add_resource(name, resource)

    def _get_ingress_ports(self):
        ports = []
        group = self._config.settings.get('security-group', {})
        for row in list(group.get('ingress', {})):
            try:
                port, source = dict(row).popitem()
            except KeyError:
                continue
            if source == 'security-group':
                ports.append(port)
        return ports
