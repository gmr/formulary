"""
Cloud Formation Network Stack Management

"""
import logging
from os import path

import yaml

from formulary import cloudformation

LOGGER = logging.getLogger(__name__)


class Network(object):
    """Create a Network cloud-formation stack consisting of the VPC,
    DHCP options, gateway configuration, routing tables, subnets, and network
    ACLs.

    """
    PATH_PREFIX = 'vpcs'

    def __init__(self, environment, config_path):
        """Create a new instance of a network stack.

        :param str environment: The environment name for the stack
        :param str config_path: Path to the formulary configuration directory

        """
        self._config_path = config_path
        self._environment = environment
        self._environment_path = path.join(self.PATH_PREFIX, environment)
        self._mappings = self._load_mappings()
        self._network = self._load_config(self._environment_path, 'network')
        self._template = self._build()

    def as_json(self):
        """Return the Network cloud formation JSON

        :rtype: str

        """
        return self._template.as_json()

    def _add_vpc(self, template):
        """Add the VPC section to the template, returning the id and name
        for use in the other sections of the stack configuration

        :param template: The template to add the VPC to
        :type template: formulary.cloudformation.Template
        :rtype: str, str

        """
        vpc_id = ''.join(x.capitalize() for x in self._environment.split('-'))
        vpc_name = self._environment.replace('-', '_')

        template.add_resource(vpc_id, _VPC(
            vpc_name, self._network['vpc']['dns-support'],
            self._network['vpc']['dns-hostnames'], self._network['cidr']))
        return vpc_id, vpc_name

    def _add_dhcp(self, template, vpc_id):
        """Add all of the DHCP options to the template for the given VPC

        :param template: The template to add the VPC to
        :type template: formulary.cloudformation.Template
        :param str vpc_id: The VPC to add the DHCP configuration to

        """
        dhcp_id = self._add_dhcp_options(template, vpc_id)
        self._add_dhcp_association(template, vpc_id, dhcp_id)

    def _add_dhcp_options(self, template, vpc_id):
        """Add all of the DHCP options to the template for the given VPC

        :param template: The template to add the VPC to
        :type template: formulary.cloudformation.Template
        :param str vpc_id: The VPC to add the DHCP options to
        :rtype: str

        """
        config = self._network['dhcp-options']
        dhcp_id = '{0}Dhcp'.format(vpc_id)
        template.add_resource(dhcp_id, _DHCPOptions(config['domain-name'],
                                                    config['name-servers'],
                                                    config['ntp-servers']))
        return dhcp_id

    @staticmethod
    def _add_dhcp_association(template, vpc_id, dhcp_id):
        """Add all of the DHCP OptionsAssociation to the template for the given
        VPC and DHCP Options ID.

        :param template: The template to add the VPC to
        :type template: formulary.cloudformation.Template
        :param str vpc_id: The VPC to associate the DHCP options with
        :param str dhcp_id: The DHCP options identifier

        """
        template.add_resource('{0}Assoc'.format(dhcp_id),
                              _DHCPOptionsAssociation(dhcp_id, vpc_id))

    @staticmethod
    def _add_gateway(template, vpc_id):
        """Add a gateway to the template for the specified VPC

        :param template: The template to add the VPC to
        :type template: formulary.cloudformation.Template
        :param str vpc_id: The VPC to add the gateway to
        :rtype: str

        """
        gateway_id = '{0}Gateway'.format(vpc_id)
        template.add_resource(gateway_id, _Gateway())
        return gateway_id

    @staticmethod
    def _add_gateway_attachment(template, vpc_id, gateway_id):
        """Attach the specified gateway to the VPC

        :param template: The template to add the VPC to
        :type template: formulary.cloudformation.Template
        :param str vpc_id: The VPC to associate the gateway with
        :param str gateway_id: The gateway
        :rtype: str

        """
        internet_gateway_id = '{0}Attachment'.format(gateway_id)
        template.add_resource(internet_gateway_id,
                              _GatewayAttachment(vpc_id, gateway_id))
        return internet_gateway_id

    @staticmethod
    def _add_network_acl(template, index, acl_id, acl):
        """Add an entry for the specified ACL

        :param template: The template to add the VPC to
        :type template: formulary.cloudformation.Template
        :param int index: The entry offset in the list
        :param str acl_id: The ALC to add the entry to
        :param dict acl: The ACL configuration

        """
        entry_id = '{0}{1}'.format(acl_id, index)
        template.add_resource(entry_id, _NetworkACLEntry(
            acl_id, acl['cidr'], acl['number'], acl['protocol'], acl['action'],
            acl['egress'], acl['ports']))

    def _add_network_acls(self, template, vpc_id, vpc_name):
        """Add Network ACLs for the specified VPC

        :param template: The template to add the VPC to
        :type template: formulary.cloudformation.Template
        :param str vpc_id: The VPC ID to associate the gateway with
        :param str vpc_name: The VPC name to associate the gateway with

        """
        acl_id = '{0}Acl'.format(vpc_id)
        template.add_resource(acl_id, _NetworkACL(vpc_name, vpc_id))
        for index, acl in enumerate(self._network['network-acls']):
            self._add_network_acl(template, index, acl_id, acl)

    @staticmethod
    def _add_public_route(template, vpc_id, route_table_id, gateway_id,
                          internet_gateway_id):
        """Add the public route specified in the mapping ``pubic/cidr`` for
        the specified VPC, route table, gateway and internet gateway.

        :param template: The template to add the VPC to
        :type template: formulary.cloudformation.Template
        :param str vpc_id: The VPC ID to associate the route with
        :param str route_table_id: The route table
        :param str gateway_id: The gateway
        :param str internet_gateway_id: The internet gateway

        """
        template.add_resource('{0}Route'.format(vpc_id),
                              _Route(route_table_id,
                                     {'Fn::FindInMap': ['public', 'cidr']},
                                     {'Ref': gateway_id}, internet_gateway_id))

    @staticmethod
    def _add_route_table(template, vpc_id):
        """Add the the route table for the specified VPC

        :param template: The template to add the VPC to
        :type template: formulary.cloudformation.Template
        :param str vpc_id: The VPC ID to associate the route table with
        :rtype: str

        """
        route_table_id = '{0}RouteTable'.format(vpc_id)
        template.add_resource(route_table_id, _RouteTable(vpc_id))
        return route_table_id

    def _add_routing(self, template, vpc_id):
        """Add all of the routing configuration for the specified VPC

        :param template: The template to add the VPC to
        :type template: formulary.cloudformation.Template
        :param str vpc_id: The VPC ID to associate the route table with
        :rtype: str

        """
        gateway_id = self._add_gateway(template, vpc_id)
        internet_gateway_id = self._add_gateway_attachment(template, vpc_id,
                                                           gateway_id)
        route_table_id = self._add_route_table(template, vpc_id)
        self._add_public_route(template, vpc_id, route_table_id, gateway_id,
                               internet_gateway_id)
        return route_table_id

    def _add_subnet(self, template, subnet, vpc_id, vpc_name, route_table_id):
        """Add the subnet for the specified VPC and route table

        :param template: The template to add the VPC to
        :type template: formulary.cloudformation.Template
        :param str subnet: The subnet name
        :param str vpc_id: The VPC ID to associate the subnet with
        :param str vpc_name: The VPC name
        :param str route_table_id: The route table

        """
        subnet_cfg = self._network['subnets'][subnet]
        subnet_id = '{0}{1}Subnet'.format(vpc_id, subnet)
        template.add_resource(subnet_id,
                              _Subnet(vpc_name, subnet, vpc_id,
                                      subnet_cfg['az'], subnet_cfg['cidr']))
        subnet_route_association = '{0}Assoc'.format(subnet_id)
        template.add_resource(subnet_route_association,
                              _SubnetRouteTableAssociation(subnet_id,
                                                           route_table_id))

    def _add_subnets(self, template, vpc_id, vpc_name, route_table_id):
        """Add the network subnets for the specified VPC and route table

        :param template: The template to add the VPC to
        :type template: formulary.cloudformation.Template
        :param str subnet: The subnet name
        :param str vpc_id: The VPC ID to associate the subnets with
        :param str vpc_name: The VPC name
        :param str route_table_id: The route table

        """
        for subnet in self._network['subnets']:
            self._add_subnet(template, subnet, vpc_id, vpc_name, route_table_id)

    def _build(self):
        """Build the Cloud Formation template for the network stack

        :rtype: formulary.cloudformation.Template

        """
        template = cloudformation.Template()
        vpc_id, vpc_name = self._add_vpc(template)
        self._add_dhcp(template, vpc_id)
        self._add_network_acls(template, vpc_id, vpc_name)
        route_table_id = self._add_routing(template, vpc_id)
        self._add_subnets(template, vpc_id, vpc_name, route_table_id)
        return template

    def _load_config(self, cfg_path, name):
        """Load YAML configuration for the specified name from the path.

        :param str cfg_path: The path prefix for the config file
        :param str name: The name of the config file
        :rtype: dict

        """
        config_file = path.normpath(path.join(self._config_path, cfg_path,
                                              '{0}.yaml'.format(name)))
        if path.exists(config_file):
            with open(config_file) as handle:
                return yaml.load(handle)

    def _load_mappings(self):
        """Load the mapping files for the template, pulling in first the top
        level mappings, then the environment specific VPC mappings.

        :rtype: dict

        """
        mappings = self._load_config('.', 'mapping')
        mappings.update(self._load_config(self._environment_path, 'mapping')
                        or {})
        return mappings


class _VPC(cloudformation.Resource):
    def __init__(self, name, dns_support, dns_hostnames, cidr_block):
        super(_VPC, self).__init__('AWS::EC2::VPC')
        self._name = name
        self._properties['EnableDnsSupport'] = dns_support
        self._properties['EnableDnsHostnames'] = dns_hostnames
        self._properties['CidrBlock'] = cidr_block


class _DHCPOptions(cloudformation.Resource):
    def __init__(self, domain_name, name_servers, ntp_servers):
        super(_DHCPOptions, self).__init__('AWS::EC2::DHCPOptions')
        self._properties['DomainName'] = domain_name
        self._properties['DomainNameServers'] = name_servers
        self._properties['NtpServers'] = ntp_servers


class _DHCPOptionsAssociation(cloudformation.Resource):
    def __init__(self, dhcp_id, vpc_id):
        super(_DHCPOptionsAssociation,
              self).__init__('AWS::EC2::VPCDHCPOptionsAssociation')
        self._properties['DhcpOptionsId'] = {'Ref': dhcp_id}
        self._properties['VpcId'] = {'Ref': vpc_id}


class _Gateway(cloudformation.Resource):
    def __init__(self):
        super(_Gateway, self).__init__('AWS::EC2::InternetGateway')


class _GatewayAttachment(cloudformation.Resource):
    def __init__(self, vpc_id, gateway_id):
        super(_GatewayAttachment,
              self).__init__('AWS::EC2::VPCGatewayAttachment')
        self._properties['InternetGatewayId'] = {'Ref': gateway_id}
        self._properties['VpcId'] = {'Ref': vpc_id}


class _RouteTable(cloudformation.Resource):
    def __init__(self, vpc_id):
        super(_RouteTable, self).__init__('AWS::EC2::RouteTable')
        self._properties['VpcId'] = {'Ref': vpc_id}


class _Route(cloudformation.Resource):
    def __init__(self, route_table_id, cidr_block, gateway_id, depends_on):
        super(_Route, self).__init__('AWS::EC2::Route')
        self._properties['RouteTableId'] = {'Ref': route_table_id}
        self._properties['DestinationCidrBlock'] = cidr_block
        self._properties['GatewayId'] = {'Ref': gateway_id}
        self._attributes['DependsOn'] = depends_on


class _Subnet(cloudformation.Resource):
    def __init__(self, vpc_name, subnet, vpc_id, az, cidr_block):
        super(_Subnet, self).__init__('AWS::EC2::Subnet')
        self._name = '{0}{1}_subnet'.format(vpc_name, subnet)
        self._properties['AvailabilityZone'] = az
        self._properties['CidrBlock'] = cidr_block
        self._properties['VpcId'] = {'Ref': vpc_id}


class _SubnetRouteTableAssociation(cloudformation.Resource):
    def __init__(self, subnet_id, route_table_id):
        super(_SubnetRouteTableAssociation,
              self).__init__('AWS::EC2::SubnetRouteTableAssociation')
        self._properties['SubnetId'] = {'Ref': subnet_id}
        self._properties['RouteTableId'] = {'Ref': route_table_id}


class _NetworkACL(cloudformation.Resource):
    def __init__(self, vpc_name, vpc_id):
        super(_NetworkACL, self).__init__('AWS::EC2::NetworkAcl')
        self._name = '{0}_acl'.format(vpc_name)
        self._properties['VpcId'] = {'Ref': vpc_id}


class _NetworkACLEntry(cloudformation.Resource):
    def __init__(self, acl_id, cidr_block, rule_number, protocol, action,
                 egress, ports):
        super(_NetworkACLEntry, self).__init__('AWS::EC2::NetworkAclEntry')
        self._properties['NetworkAclId'] = {'Ref': acl_id}
        self._properties['CidrBlock'] = cidr_block
        self._properties['RuleNumber'] = rule_number
        self._properties['Protocol'] = protocol
        self._properties['RuleAction'] = action
        self._properties['Egresss'] = egress
        ports = ports.split('-') if ports else (0, 65536)
        port_range = {'From': ports[0], 'To': ports[1]}
        self._properties['PortRange'] = port_range
