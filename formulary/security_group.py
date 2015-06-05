"""
Security Group Resources

"""
from formulary import cloudformation
from formulary import network


class TemplateWithSecurityGroup(cloudformation.Template):

    PARENT_CONFIG_PREFIX = 'vpcs'

    def __init__(self, name, parent, config_path, region='us-east-1'):
        """Create a new instance of a RDS stack.

        :param str name: The environment name for the stack
        :param str config_path: Path to the formulary configuration directory

        """
        super(TemplateWithSecurityGroup, self).__init__(name, parent,
                                                        config_path)
        self._environment = 'unknown'
        self._region = region
        self._network_stack = None
        self._security_group = None

    def _add_network_mappings(self):
        vpc = dict()
        for key, value in self._network_stack.vpc._asdict().items():
            cckey = self._to_camel_case(key)
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

    def _add_security_group(self):
        if isinstance(self._config.get('security-group'), str):
            return self._config.get('security-group')

        environment = self._network_stack.environment
        desc = ('Security Group for the {0} '
                'service in {1}').format(self._name.capitalize(),
                                         environment.capitalize())
        resource = _SecurityGroup('{0}-service'.format(self.name), desc,
                                  self._network_stack.vpc.id,
                                  self._build_ingress_rules())
        self._add_environment_tag(resource)
        name = '{0}{1}{2}SecurityGroup'.format(environment.capitalize(),
                                               self.STACK_TYPE.capitalize(),
                                               self._to_camel_case(self._name))
        self.add_resource(name, resource)
        return {'Ref': name}

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

    def _init_network_stack(self):
        self._network_stack = network.NetworkStack(self._parent,
                                                   self._config_path,
                                                   self._region)
        self._add_network_mappings()
        self._environment = self._network_stack.environment


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
