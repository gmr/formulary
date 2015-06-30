"""
Build Cloud Formation EC2 stacks

"""
import json
import re

from formulary.builders import base
from formulary.resources import ec2
from formulary import s3
from formulary import utils


DEFAULT_INSTANCE_TYPE = 't2.small'
USER_DATA_RE = re.compile(r'\{\^(?P<command>instance|map)\s(?P<key>[\w\.]+)\}')
USER_DATA_JSON = re.compile(r'(\{\"(?:Ref|Fn\::\w+)\"[\s\:]+'
                            r'(?:\".*?\"|\[.*?\])\})')


class Instance(base.Builder):

    def __init__(self, config, name, ami, block_devices, instance_type,
                 private_ip, security_group, subnet, user_data, tags):
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

        """
        super(Instance, self).__init__(config, name)
        self._s3 = s3.S3(config.s3_bucket, config.s3_prefix, config.profile)
        full_name = '{0}-service-{1}'.format(config.environment, name)

        # Build kwargs used for user-data template and ec2.Instance
        kwargs = {'name': full_name,
                  'ami': ami,
                  'availability_zone': subnet.availability_zone,
                  'block_devices': block_devices,
                  'environment': config.environment,
                  'instance_type': instance_type,
                  'private_ip': private_ip,
                  'ref_id': utils.camel_case(full_name),
                  'region': config.region,
                  'service': config.service,
                  'subnet': subnet.id,
                  'security_group': security_group}

        kwargs['user_data'] = self._render_user_data(user_data, kwargs)

        # Remove the kwargs that don't get passed to ec2.Instance
        for key in ['environment', 'ref_id', 'region', 'service']:
            del kwargs[key]

        resource = ec2.Instance(**kwargs)
        for key, value in tags.items():
            resource.add_tag(key, value)
        ref_id = self._add_resource(full_name, resource)

        # Add private and public IP output
        self._add_output('PrivateIP',
                         'Private IP address for {0}'.format(full_name),
                         {'Fn::GetAtt': [ref_id, 'PrivateIp']})
        self._add_output('PublicIP',
                         'Public IP address for {0}'.format(full_name),
                         {'Fn::GetAtt': [ref_id, 'PublicIp']})

    def _render_user_data(self, content, kwargs):
        for match in USER_DATA_RE.finditer(content):
            if match.group(1) == 'map':
                value = self._config.mappings
                for key in str(match.group(2)).split('.'):
                    value = value.get(key.strip())
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
