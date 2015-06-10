"""
Build the resources for a Security Group

"""
from formulary import base
from formulary import resources
from formulary import utils

class SecurityGroup(base.Builder):

    def __init__(self, config, name, environment, mappings, stack):
        super(SecurityGroup, self).__init__(config, name, environment, mappings)
        self._owner = name
        self._name = '{0}-{1}-security-group'.format(environment, name)
        self._stack = stack
        self.logical_id = self._add_security_group()

    def _add_security_group(self):
        if isinstance(self._config.get('security-group'), str):
            return self._config.get('security-group')

        desc = ('Security Group for the {0} '
                'service in {1}').format(self._owner.capitalize(),
                                         self._stack.environment.capitalize())
        resource = resources.SecurityGroup(self._name,
                                           desc,
                                           self._stack.vpc.id,
                                           self._build_ingress_rules())
        self._add_resource(self._name, resource)
        return self._name

    def _build_ingress_rules(self):
        rules = []
        group = self._config.get('security-group', {})
        ingress_rules = list(group.get('ingress', {}))
        for row in ingress_rules:
            try:
                port, source = dict(row).popitem()
            except KeyError:
                continue
            protocol, from_port, to_port = utils.parse_port_value(port)
            cidr_block = utils.find_in_map(source)
            rules.append(resources.SecurityGroupRule(protocol,
                                                     from_port, to_port,
                                                     cidr_block).as_dict())
        return rules
