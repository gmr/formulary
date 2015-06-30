"""
Build the resources for a Security Group

"""
from formulary.builders import base
from formulary.resources import ec2
from formulary import utils

class SecurityGroup(base.Builder):

    def __init__(self, config, name, stack):
        super(SecurityGroup, self).__init__(config, name)
        self._owner = name
        self._name = '{0}-{1}-security-group'.format(self._config.environment,
                                                     name)
        self._stack = stack
        self._add_security_group()
        self._add_output('SecurityGroupId',
                         'The physical ID for the security group',
                         {'Ref': utils.camel_case(self._name)})

    @property
    def logical_id(self):
        return self.name

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
            protocol, from_port, to_port = utils.parse_port_value(port)
            cidr_block = utils.find_in_map(source)
            rules.append(ec2.SecurityGroupRule(protocol,
                                               from_port, to_port,
                                               cidr_block).as_dict())
        return rules
