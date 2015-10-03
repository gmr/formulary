"""
Manage the full VPC stack

"""
import troposphere
from troposphere import ec2

from formulary.stacks import base
from formulary import utils

DEFAULT_ACL_ACTION = 'allow'
DEFAULT_ACL_EGRESS = False
DEFAULT_CIDR = '192.168.0.0/16'
DEFAULT_DESCRIPTION = 'Formulary created VPC'
DEFAULT_DNS_HOSTNAMES = True
DEFAULT_DNS_SUPPORT = True
DEFAULT_NAME_SERVERS = ['AmazonProvidedDNS']
DEFAULT_TENANCY = 'default'

PUBLIC_CIDR = '0.0.0.0/0'


class VPC(base.Stack):
    """Defines a template for the entire VPC stack including DHCP, Internet
    gateway, routing, subnets, and ACLs

    """
    def __init__(self, config, name):
        super(VPC, self).__init__(config, name, name)
        self._template.description = config.get('description',
                                                DEFAULT_DESCRIPTION)
        self._add_vpc()
        self._add_dhcp()
        gateway = self._add_gateway()
        self._add_gateway_attachment(gateway)
        route_table = self._add_route_table()
        self._add_public_route(route_table, gateway)
        acl = self._add_network_acl()
        self._add_network_acl_entries(acl)
        self._add_subnets(route_table)
        self._add_outputs()

    def _add_dhcp(self):
        """Add all of the DHCP options to the template for the given VPC"""
        self._add_dhcp_association(self._add_dhcp_options())

    def _add_dhcp_options(self):
        """Add all of the DHCP options to the template for the given VPC

        :rtype: str

        """
        name = '{}-dhcp'.format(self.name)
        title = utils.camel_case(name)
        options = ec2.DHCPOptions(title)
        config = self._config.get('dhcp-options', {})
        if config.get('domain-name'):
            options.DomainName = config['domain-name']
        options.DomainNameServers = config.get('name-servers',
                                               DEFAULT_NAME_SERVERS)
        if config.get('netbios-name-servers'):
            options.NetbiosNameServers = config['netbios-name-servers']
        if config.get('netbios-node-type'):
            options.NetbiosNodeType = config['netbios-node-type']
        if config.get('ntp-servers'):
            options.NtpServers = config['ntp-servers']
        options.Tags = troposphere.Tags(Name=name, VPC=self.ref)
        self._add_resource(options)
        return title

    def _add_dhcp_association(self, dhcp_options_title):
        """Add all of the DHCP OptionsAssociation to the template for the given
        VPC and DHCP Options ID.

        :param str dhcp_options_title: The DHCP Options Id
        :rtype: str

        """
        title = '{}DhcpAssoc'.format(self.ref)
        assoc = ec2.VPCDHCPOptionsAssociation(title)
        assoc.DhcpOptionsId = troposphere.Ref(dhcp_options_title)
        assoc.VpcId = troposphere.Ref(self.ref)
        self._add_resource(assoc)
        return title

    def _add_gateway(self):
        """Add a gateway to the template for the specified VPC

        :rtype: str

        """
        name = '{}-gateway'.format(self.name)
        title = utils.camel_case(name)
        gateway = ec2.InternetGateway(title)
        self._add_resource(gateway)
        gateway.Tags = troposphere.Tags(Name=name, VPC=self.ref)
        return title

    def _add_gateway_attachment(self, gateway):
        """Attach the specified gateway to the VPC

        :param str gateway: The gateway to attach
        :rtype: str

        """
        title = '{}Attachment'.format(gateway)
        attachment = ec2.VPCGatewayAttachment(title)
        attachment.InternetGatewayId = troposphere.Ref(gateway)
        attachment.VpcId = troposphere.Ref(self.ref)
        self._add_resource(attachment)
        return title

    def _add_network_acl(self):
        """Add the Network ACL to the VPC

        :rtype: str

        """
        name = '{}-acl'.format(self.name)
        title = utils.camel_case(name)
        acl = ec2.NetworkAcl(title)
        acl.VpcId = troposphere.Ref(self.ref)
        acl.Tags = troposphere.Tags(Name=name, VPC=self.ref)
        self._add_resource(acl)
        return title

    def _add_network_acl_entries(self, acl):
        """Iterate through the ACL entries and add them"""
        acl_ref = troposphere.Ref(acl)
        for index, value in enumerate(self._config.get('network-acls', [])):
            (protocol, from_port, to_port) = \
                utils.parse_port_value(value['ports'], -1)
            title = '{}{}'.format(acl, index)
            entry = ec2.NetworkAclEntry(title)
            entry.CidrBlock = value['cidr']
            if value.get('icmp') is not None:
                entry.Icmp = value['icmp']
            if value.get('number') is not None:
                entry.RuleNumber = value['number']
            else:
                entry.RuleNumber = index
            entry.Protocol = protocol
            entry.RuleAction = value.get('action', DEFAULT_ACL_ACTION)
            entry.Egress = value.get('egress', DEFAULT_ACL_EGRESS)

            entry.NetworkAclId = acl_ref
            entry.PortRange = ec2.PortRange(From=from_port, To=to_port)
            self._add_resource(entry)

    def _add_outputs(self):
        """Create output for the template with the VPC Id"""
        description = 'VPC Id for {}'.format(self.ref)
        output = troposphere.Output('VpcId', Description=description,
                                    Value=self.ref)
        self._add_output(output)

    def _add_public_route(self, route_table, gateway):
        """Add the public route specified in the mapping ``pubic/cidr`` for
        the specified VPC, route table, gateway and internet gateway.

        :param str route_table: The route table title
        :param str gateway: The gateway title
        :rtype: str

        """
        title = '{}Route'.format(self.ref)
        route = ec2.Route(title)
        route.DestinationCidrBlock = PUBLIC_CIDR
        route.GatewayId = troposphere.Ref(gateway)
        route.RouteTableId = troposphere.Ref(route_table)
        self._add_resource(route)
        return title

    def _add_route_table(self):
        """Add the the route table to the VPC

        :rtype: str

        """
        name = '{}-route-table'.format(self.name)
        title = utils.camel_case(name)
        route_table = ec2.RouteTable(title)
        route_table.VpcId = troposphere.Ref(self.ref)
        route_table.Tags = troposphere.Tags(Name=name, VPC=self.ref)
        self._add_resource(route_table)
        return title

    def _add_subnets(self, route_table):
        """Add the network subnets for the specified VPC and route table"""
        route_table_ref = troposphere.Ref(route_table)
        vpc_ref = troposphere.Ref(self.ref)

        for subnet in self._config.get('subnets', {}):
            config = self._config['subnets'][subnet]

            name = '{}-{}-subnet'.format(self.name, utils.camel_case(subnet))
            title = utils.camel_case(name)
            subnet = ec2.Subnet(title)
            subnet.AvailabilityZone = config['availability-zone']
            subnet.CidrBlock = config['cidr']
            subnet.VpcId = vpc_ref
            subnet.Tags = troposphere.Tags(Name=name, VPC=self.ref)
            self._add_resource(subnet)

            rt_title = '{}Assoc'.format(title)
            subnet_rt_assoc = ec2.SubnetRouteTableAssociation(rt_title)
            subnet_rt_assoc.RouteTableId = route_table_ref
            subnet_rt_assoc.SubnetId = troposphere.Ref(title)
            self._add_resource(subnet_rt_assoc)

    def _add_vpc(self):
        """Add the VPC section to the template, returning the id and name
        for use in the other sections of the stack configuration

        """
        vpc = ec2.VPC(self.ref)
        vpc.CidrBlock = self._config.get('cidr', DEFAULT_CIDR)
        vpc.EnableDnsSupport = self._config.get('dns-support',
                                                DEFAULT_DNS_SUPPORT)
        vpc.EnableDnsHostnames = self._config.get('dns-hostnames',
                                                  DEFAULT_DNS_HOSTNAMES)
        vpc.InstanceTenancy = self._config.get('tenancy', DEFAULT_TENANCY)
        vpc.Tags = troposphere.Tags(Name=self.name, VPC=self.ref)
        self._add_resource(vpc)
