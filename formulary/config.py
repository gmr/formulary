"""
Builder Configuration

"""
import logging
from os import path
import json
import sys
import yaml

import jsonschema

from formulary import aws

LOGGER = logging.getLogger(__name__)


CONFIG_FOLDERS = {'elasticache': 'elasticaches',
                  'rds': 'rds',
                  'service': 'services',
                  'stack': 'stacks',
                  'vpc': 'vpcs'}

EXTENSIONS = ['json', 'yml', 'yaml']

VPC_SCHEMA = '''
{
    "$schema": "http://json-schema.org/draft-04/schema#",
    "id": "http://jsonschema.net",
    "type": "object",
    "properties": {
        "cidr": {
            "title": "CIDR",
            "description": "The CIDR block you want the VPC to cover",
            "type": "string",
            "pattern": "^([0-9]{1,3}\\\\.){3}[0-9]{1,3}/[0-9]{1,2}$",
            "default": "192.168.0.0/16"
        },
        "description": {
            "title": "Description",
            "description": "A description of the VPC used in CloudFormation comments",
            "type": "string",
            "default": "Formulary created VPC"
        },
        "region": {
            "title": "AWS Region",
            "description": "The AWS region for the VPC",
            "type": "string",
            "enum": [
                "us-east-1",
                "us-west-1",
                "us-west-2",
                "eu-west-1",
                "eu-central-1",
                "ap-southeast-1",
                "ap-southeast-2",
                "ap-northeast-1",
                "sa-east-1"
            ],
            "default": "us-east-1"
        },
        "s3bucket": {
            "title": "S3 Bucket",
            "description": "The S3 bucket to upload CloudFormation templates for",
            "type": "string"
        },
        "dns-support": {
            "title": "DNS Support",
            "description": "Specifies whether DNS resolution is supported for the VPC",
            "type": "boolean",
            "default": true
        },
        "dns-hostnames": {
            "title": "DNS Hostnames",
            "description": "Specifies whether the instances launched in the VPC get DNS hostnames",
            "type": "boolean",
            "default": false
        },
        "tenancy": {
            "title": "Instance Tenancy",
            "description": "The allowed tenancy of instances launched into the VPC",
            "type": "string",
            "enum": [
                "default",
                "dedicated"
            ],
            "default": "default"
        },
        "dhcp-options": {
            "title": "DHCP Options",
            "description": " DHCP options for your VPC",
            "type": "object",
            "properties": {
                "domain-name": {
                    "title": "Domain Name",
                    "description": "The domain name for hosts in the VPC",
                    "type": "string",
                    "pattern": "^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\\\\-]*[a-zA-Z0-9])\\\\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\\\\-]*[A-Za-z0-9])$"
                },
                "name-servers": {
                    "title": "DomainNameServers",
                    "description": "The IP (IPv4) address of up to four domain name servers",
                    "type": "array",
                    "items": [
                        {
                            "type": "string"
                        }
                    ],
                    "minItems": 1,
                    "maxItems": 4,
                    "uniqueItems": true,
                    "default": [
                        "AmazonProvidedDNS"
                    ]
                },
                "netbios-name-servers": {
                    "title": "NetbiosNameServers",
                    "description": "The IP address (IPv4) of up to four NetBIOS name servers",
                    "type": "array",
                    "items": [
                        {
                            "type": "string"
                        }
                    ],
                    "minItems": 1,
                    "maxItems": 4,
                    "uniqueItems": true
                },
                "netbios-node-type": {
                    "title": "NetbiosNodeType",
                    "description": "An integer value indicating the NetBIOS node type",
                    "type": "integer",
                    "enum": [1, 2, 4, 8]

                },
                "ntp-servers": {
                    "title": "Ntp Servers",
                    "description": "The IP address (IPv4) of up to four Network Time Protocol (NTP) servers",
                    "type": "array",
                    "items": [
                        {
                            "type": "string"
                        }
                    ],
                    "minItems": 1,
                    "maxItems": 4,
                    "uniqueItems": true
                }
            },
            "required": [
                "domain-name",
                "name-servers"
            ]
        },
        "network-acls": {
            "title": "Network ACLs",
            "description": "An array of network ACLs for the VPC",
            "type": "array",
            "items": [
                {
                    "$ref": "#/definitions/network-acl-entry"
                }
            ],
            "minItems": 1
        },
        "subnets": {
            "title": "Subnets",
            "description": "Subnets of the VPC by availability zone",
            "type": "object",
            "patternProperties": {
                "^[a-zA-Z]$": {
                    "$ref": "#/definitions/subnet"
                }
            }
        }
    },
    "required": [
        "network-acls",
        "subnets"
    ],
    "additionalProperties": false,
    "definitions": {
        "network-acl-entry": {
            "title": "Network ACL Entry",
            "description": "An entry in the network ACLs for the VPC",
            "type": "object",
            "properties": {
                "cidr": {
                    "title": "CIDR",
                    "description": "The CIDR block for the ACL rule",
                    "type": "string",
                    "pattern": "^([0-9]{1,3}\\\\.){3}[0-9]{1,3}/[0-9]{1,2}$",
                    "default": "0.0.0.0/0"
                },
                "egress": {
                    "title": "Egress",
                    "description": "Whether this rule applies to egress traffic from the subnet (true) or ingress traffic to the subnet (false)",
                    "type": "boolean"
                },
                "protocol": {
                    "title": "IP Protocol",
                    "description": "The IP protocol that the rule applies to",
                    "type": "integer",
                    "default": -1,
                    "minimum": -1,
                    "maximum": 255
                },
                "action": {
                    "title": "Rule Action",
                    "description": "Whether to allow or deny traffic that matches the rule",
                    "type": "string",
                    "enum": [
                        "allow",
                        "deny"
                    ]
                },
                "number": {
                    "title": "Rule Number",
                    "description": "Rule number to assign to the entry (e.g., 100)",
                    "type": "integer",
                    "default": 1
                },
                "ports": {
                    "title": "Ports",
                    "description": "The range of ports for the UDP/TCP protocol",
                    "type": "string",
                    "default": "0-65535",
                    "pattern": "^[0-9]{1,5}-[0-9]{1,5}$"
                }
            },
            "additionalProperties": false,
            "required": [
                "cidr",
                "egress",
                "protocol",
                "action",
                "number",
                "ports"
            ]
        },
        "subnet": {
            "title": "Subnet",
            "description": "Creates a subnet in an existing VPC",
            "type": "object",
            "properties": {
                "availability-zone": {
                    "title": "Availability Zone",
                    "description": "The availability zone for the subnet",
                    "type": "string"
                },
                "cidr": {
                    "title": "CIDR",
                    "description": "The CIDR block of the subnet",
                    "type": "string",
                    "pattern": "^([0-9]{1,3}\\\\.){3}[0-9]{1,3}/[0-9]{1,2}$",
                    "default": "0.0.0.0/0"
                }
            },
            "additionalProperties": false,
            "required": [
                "availability-zone",
                "cidr"
            ]
        }
    }
}
'''


class Resource(object):

    def __init__(self, base_path, resource_type, resource, vpc):
        self.base_path = self._normalize_path(base_path)
        self.vpc = vpc
        self._resource = resource
        self._resource_type = resource_type

    def _flatten_config(self, cfg):
        """Take a given config dictionary and if it contains vpc
        specific values, map the vpc values to the associated
        top level keys.

        :param dict cfg: The configuration to flatten
        :rtype: dict

        """
        output = {}
        for key, value in cfg.items():
            if isinstance(value, dict):
                if self.vpc in value.keys():
                    output[key] = value[self.vpc]
                else:
                    output[key] = self._flatten_config(value)
            elif isinstance(value, list):
                output[key] = []
                for list_value in value:
                    if isinstance(list_value, dict):
                        output[key].append(self._flatten_config(list_value))
                    else:
                        output[key].append(list_value)
            else:
                output[key] = value
        return output

    @staticmethod
    def get_file_path(base_path, filename):
        """Returns the path to the file for the given config path, folder,
        and filename.

        :param str base_path: The base path of the file
        :param str filename: The base filename without the extension
        :rtype: str|None

        """
        for extension in EXTENSIONS:
            file_path = path.join(base_path, '.'.join([filename, extension]))
            if path.exists(file_path):
                return file_path

    def load(self):
        """Return the config for the specified resource type

        :rtype: dict

        """
        if self._resource_type in ['vpc', 'service']:
            settings = self.load_file(self.resource_folder, self._resource_type)
        else:
            settings = self.load_file(self.resource_folder, self._resource)
        return self._flatten_config(settings)

    def load_file(self, folder, file):
        """Return the contents of the specified configuration file in the
        specified configuration folder.


        :param str folder: The folder to load the configuration file from
        :param str file: The file to load
        :rtype: dict

        """
        file_path = self.get_file_path(folder, file)
        if file_path:
            LOGGER.debug('Loading configuration from %s', file_path)
            return self.load_and_deserialize_file(file_path)
        LOGGER.debug('Configuration file not found: %s', file)
        return {}

    @staticmethod
    def load_and_deserialize_file(file_path):
        """Load a file and parse it with the correct serialization format
        based upon the file extension

        :param str file_path: The path to the file to load
        :rtype: dict

        """
        if file_path.endswith('yml') or file_path.endswith('yaml'):
            return yaml.load(open(file_path, 'r'))
        elif file_path.endswith('json'):
            return json.load(open(file_path, 'r'))

    def mappings(self):
        """Return the mapping data from the various config dirs and return
        merged mapping values in order of precedence of global, vpc,
        or service/entity.

        :rtype: dict

        """
        mappings = dict()
        mappings.update(self.load_file(self.base_path, 'mappings'))
        if not self._resource == 'vpc':
            self.merge(mappings, self.vpc_mappings())
        mappings.update(self.load_file(self.resource_folder, 'mappings'))
        return mappings

    def merge(self, a, b, key_path=None):
        if key_path is None: key_path = []
        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    self.merge(a[key], b[key], key_path + [str(key)])
            else:
                a[key] = b[key]
        return a

    @staticmethod
    def _normalize_path(value): # pragma: no cover
        """Normalize the specified path value returning the absolute
        path for it.

        :param str value: The path value to normalize
        :rtype: str

        """
        return path.abspath(path.normpath(value))

    @property
    def resource_folder(self):
        """Return the folder that contains the resource's configuration data

        :rtype: str

        """
        if self._resource_type in ['vpc', 'service']:
            return path.join(self.base_path,
                             CONFIG_FOLDERS[self._resource_type],
                             self._resource)
        return path.join(self.base_path, CONFIG_FOLDERS[self._resource_type])

    @staticmethod
    def validate_config_path(config_path):
        """Validate that the specified configuration path exists and
        contains at least some of the files or folders expected.

        :param str config_path: The path to validate
        :rtype: bool

        """
        paths_found = [path.exists(config_path)]
        paths_found += [path.exists(path.join(config_path, f)) for f in
                        CONFIG_FOLDERS.values()]
        return any(paths_found)

    def validate_vpc(self, env):
        """Validate that the expected VPC configuration file exists within the
        config path for the vpc.

        :param str env: The vpc name
        :rtype: bool

        """
        if not env:
            return False

        config = self.vpc_config()
        if not config:
            return False

        try:
            jsonschema.validate(config, json.loads(VPC_SCHEMA))
        except jsonschema.exceptions.ValidationError:
            sys.stderr.write('Error validating VPC configuration:\n\n')
            v = jsonschema.Draft4Validator(json.loads(VPC_SCHEMA))
            for err in sorted(v.iter_errors(config), key=str):
                sys.stderr.write(' - {} in: \n\n   {}\n\n'.format(err.message,
                                                                  err.instance))
            return False
        return True

    def vpc_config(self):
        """Return the vpc configuration

        :rtype: dict

        """
        if self._resource_type == 'vpc':
            return self.load()
        elif not self.vpc:
            return {}
        return self.load_file(self.resource_folder, 'vpc')

    def vpc_mappings(self):
        """Return the mappings from the vpc folder

        :rtype: dict

        """
        if not self.vpc:
            return {}
        return self.load_file(self.resource_folder, 'mappings')


class Stack(object):

    """Configuration class for Stack objects"""
    def __init__(self, base_path, resource_type, resource_name, vpc,
                 aws_profile=None):
        """Create a new instance of a Stack configuration obj

        """
        config = Resource(base_path, resource_type, resource_name, vpc)

        self._aws_profile = aws_profile
        self._base_path = base_path
        self._resource_name = resource_name
        self._resource_type = resource_type
        self._vpc_name = vpc

        self._vpc_stack = aws.VPCStack(vpc, config.vpc_config(), None,
                                       aws_profile)

        self._amis = config.load_file('.', 'amis')
        self._mappings = config.mappings()
        self._settings = config.load()

    @property
    def subnets(self):
        """Return a list of Subnet IDs for the VPC

        :rtype: list

        """
        return [s.id for s in self._vpc_stack.subnets]


