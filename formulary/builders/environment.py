"""
Build the AWS VPC environment by adding the various resources to the
Cloud Formation template

"""

from formulary.builders import base
from formulary.resources import ec2
from formulary import utils


class Environment(base.Builder):

    def __init__(self, config, name):
        super(Environment, self).__init__(config, name)
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
        resource = ec2.VPC(vpc_name,
                           self._config.settings['vpc']['dns-support'],
                           self._config.settings['vpc']['dns-hostnames'],
                           self._config.settings['CIDR'])
        resource.add_tag('Environment', self._config.settings['environment'])
        return self._add_resource(vpc_name, resource), vpc_name

    def _add_dhcp(self):
        """Add all of the DHCP options to the template for the given VPC"""
        self._add_dhcp_association(self._add_dhcp_options())

    def _add_dhcp_options(self):
        """Add all of the DHCP options to the template for the given VPC

        :rtype: str

        """
        config = self._config.settings['dhcp-options']
        options = '{0}-dhcp'.format(self._vpc_name)
        self._add_resource(options,
                           ec2.DHCPOptions(config['domain-name'],
                                           config['name-servers'],
                                           config['ntp-servers']))
        return options

    def _add_dhcp_association(self, dhcp_id):
        """Add all of the DHCP OptionsAssociation to the template for the given
        VPC and DHCP Options ID.

        :param str dhcp_id: The DHCP Options ID

        """
        dhcp = {'Ref': utils.camel_case(dhcp_id)}
        vpc_id = {'Ref': utils.camel_case(self._vpc_name)}
        self._add_resource('{0}-dhcp-assoc'.format(dhcp_id),
                           ec2.VPCDHCPOptionsAssociation(dhcp, vpc_id))

    def _add_gateway(self):
        """Add a gateway to the template for the specified VPC

        :rtype: str

        """
        gateway = '{0}-gateway'.format(self._vpc_name)
        self._add_resource(gateway, ec2.InternetGateway())
        return gateway

    def _add_gateway_attachment(self):
        """Attach the specified gateway to the VPC

        :rtype: str

        """
        attachment = '{0}-attachment'.format(self._gateway)
        gateway_id = {'Ref': utils.camel_case(self._gateway)}
        vpc_id = {'Ref': utils.camel_case(self._vpc_name)}
        self._add_resource(attachment,
                           ec2.VPCGatewayAttachment(gateway_id, vpc_id))
        return attachment

    def _add_network_acl(self):
        """Add the Network ACL to the VPC

        :rtype: str

        """
        resource = ec2.NetworkACL(self._vpc_name,
                                  {'Ref': utils.camel_case(self._vpc_name)})
        resource.add_tag('Environment', self._config.settings['environment'])
        acl = '{0}-network-acl'.format(self._vpc_name)
        self._add_resource(acl, resource)
        return acl

    def _add_network_acl_entries(self):
        """Iterate through the ACL entries and add them"""
        acl_id = {'Ref': utils.camel_case(self._acl)}
        for index, acl in enumerate(self._config.settings['network-acls']):
            self._add_resource('{0}{1}'.format(self._acl, index),
                               ec2.NetworkACLEntry(acl_id,
                                                   acl['CIDR'],
                                                   acl['number'], acl['action'],
                                                   acl['egress'], acl['ports']))

    def _add_public_route(self):
        """Add the public route specified in the mapping ``pubic/cidr`` for
        the specified VPC, route table, gateway and internet gateway.

        """
        route_table_id = {'Ref': utils.camel_case(self._route_table)}
        gateway_id = {'Ref': utils.camel_case(self._gateway)}
        internet_gateway_id = utils.camel_case(self._internet_gateway)
        self._add_resource('{0}-route'.format(self._vpc_name),
                           ec2.Route(route_table_id,
                                     {'Fn::FindInMap': ['SubnetConfig',
                                                        'Public',
                                                        'CIDR']},
                                     gateway_id, internet_gateway_id))

    def _add_route_table(self,):
        """Add the the route table for the specified VPC

        :rtype: str

        """
        route_table = '{0}-route-table'.format(self._vpc_name)
        vpc_name = {'Ref': utils.camel_case(self._vpc_name)}
        self._add_resource(route_table, ec2.RouteTable(vpc_name))
        return route_table

    def _add_subnets(self):
        """Add the network subnets for the specified VPC and route table"""
        subnet_ids = []
        route_table_id = {'Ref': utils.camel_case(self._route_table)}
        vpc_id = {'Ref': utils.camel_case(self._vpc_name)}

        for subnet in self._config.settings['subnets']:
            config = self._config.settings['subnets'][subnet]

            subnet_id = '{0}{1}-subnet'.format(self._vpc_name, subnet)

            subnet_ids.append(utils.camel_case(subnet_id))
            resource = ec2.Subnet(self._vpc_name, subnet,
                                  vpc_id,
                                  config['availability_zone'],
                                  config['CIDR'])

            resource.add_tag('Environment',
                             self._config.settings['environment'])

            self._add_resource(subnet_id, resource)
            subnet_ref = {'Ref': utils.camel_case(subnet_id)}

            self._add_resource('{0}-assoc'.format(subnet_id),
                               ec2.SubnetRouteTableAssociation(subnet_ref,
                                                               route_table_id))
