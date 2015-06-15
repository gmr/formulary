"""
Build the AWS VPC environment by adding the various resources to the
Cloud Formation template

"""

from formulary import base
from formulary import resources
from formulary import utils


class Environment(base.Builder):

    def __init__(self, config, name, mappings):
        super(Environment, self).__init__(config, name, None, mappings)
        self._vpc, self._vpc_name = self._add_vpc()
        self._add_dhcp()
        self._gateway = self._add_gateway()
        self._internet_gateway = self._add_gateway_attachment()
        self._route_table = self._add_route_table()
        self._add_public_route()
        self._acl = self._add_network_acl()
        self._add_network_acl_entries()
        self._add_subnets()
        self._add_output('VPCId', 'VPC ID for {0}'.format(self._vpc_name),
                         self._vpc)

    def _add_vpc(self):
        """Add the VPC section to the template, returning the id and name
        for use in the other sections of the stack configuration

        :rtype: str, str

        """
        vpc_name = self._name.replace('_', '-')
        resource = resources.VPC(vpc_name,
                                 self._config['vpc']['dns-support'],
                                 self._config['vpc']['dns-hostnames'],
                                 self._config['CIDR'])
        resource.add_tag('Environment', self._config['environment'])
        return self._add_resource(vpc_name, resource), vpc_name

    def _add_dhcp(self):
        """Add all of the DHCP options to the template for the given VPC"""
        self._add_dhcp_association(self._add_dhcp_options())

    def _add_dhcp_options(self):
        """Add all of the DHCP options to the template for the given VPC

        :rtype: str

        """
        config = self._config['dhcp-options']
        options = '{0}-dhcp'.format(self._vpc_name)
        self._add_resource(options,
                           resources.DHCPOptions(config['domain-name'],
                                                 config['name-servers'],
                                                 config['ntp-servers']))
        return options

    def _add_dhcp_association(self, dhcp_id):
        """Add all of the DHCP OptionsAssociation to the template for the given
        VPC and DHCP Options ID.

        :param str dhcp_id: The DHCP Options ID

        """
        self._add_resource('{0}-dhcp-assoc'.format(dhcp_id),
                           resources.DHCPOptionsAssociation(
                               utils.camel_case(dhcp_id),
                               utils.camel_case(self._vpc_name)))

    def _add_gateway(self):
        """Add a gateway to the template for the specified VPC

        :rtype: str

        """
        gateway = '{0}-gateway'.format(self._vpc_name)
        self._add_resource(gateway, resources.Gateway())
        return gateway

    def _add_gateway_attachment(self):
        """Attach the specified gateway to the VPC

        :rtype: str

        """
        attachment = '{0}-attachment'.format(self._gateway)
        self._add_resource(attachment,
                           resources.GatewayAttachment(
                               utils.camel_case(self._vpc_name),
                               utils.camel_case(self._gateway)))
        return attachment

    def _add_network_acl(self):
        """Add the Network ACL to the VPC

        :rtype: str

        """
        resource = resources.NetworkACL(self._vpc_name, self._vpc)
        resource.add_tag('Environment', self._config['environment'])
        acl = '{0}-network-acl'.format(self._vpc_name)
        self._add_resource(acl, resource)
        return acl

    def _add_network_acl_entries(self):
        """Iterate through the ACL entries and add them"""
        for index, acl in enumerate(self._config['network-acls']):
            self._add_resource('{0}{1}'.format(self._acl, index),
                               resources.NetworkACLEntry(
                                   utils.camel_case(self._acl),
                                   acl['CIDR'], acl['number'], acl['action'],
                                   acl['egress'], acl['ports']))

    def _add_public_route(self):
        """Add the public route specified in the mapping ``pubic/cidr`` for
        the specified VPC, route table, gateway and internet gateway.

        """
        self._add_resource('{0}-route'.format(self._vpc_name),
                           resources.Route(
                               utils.camel_case(self._route_table),
                               {'Fn::FindInMap': ['SubnetConfig',
                                                  'Public',
                                                  'CIDR']},
                               utils.camel_case(self._gateway),
                               utils.camel_case(self._internet_gateway)))

    def _add_route_table(self,):
        """Add the the route table for the specified VPC

        :rtype: str

        """
        route_table = '{0}-route-table'.format(self._vpc_name)
        self._add_resource(route_table,
                           resources.RouteTable(
                               utils.camel_case(self._vpc_name)))
        return route_table

    def _add_subnets(self):
        """Add the network subnets for the specified VPC and route table"""
        subnet_ids = []
        for subnet in self._config['subnets']:
            config = self._config['subnets'][subnet]
            subnet_id = '{0}{1}-subnet'.format(self._vpc_name, subnet)
            subnet_ids.append(utils.camel_case(subnet_id))
            resource = resources.Subnet(self._vpc_name, subnet, self._vpc,
                                        config['availability_zone'],
                                        config['CIDR'])
            resource.add_tag('Environment', self._config['environment'])
            self._add_resource(subnet_id, resource)
            self._add_resource('{0}-assoc'.format(subnet_id),
                               resources.SubnetRouteTableAssociation(
                                   utils.camel_case(subnet_id),
                                   utils.camel_case((self._route_table))))
