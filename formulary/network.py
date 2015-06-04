"""
Cloud Formation Network Stack Management

"""
import logging
from os import path

import yaml

from formulary import cloudformation

LOGGER = logging.getLogger(__name__)


class NetworkStackTemplate(cloudformation.Template):
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
        super(NetworkStackTemplate, self).__init__()
        self._config_path = config_path
        self._environment = environment
        self._environment_path = path.join(self.PATH_PREFIX, environment)
        self._mappings = self._load_mappings()
        self._network = self._load_config(self._environment_path, 'network')
        self._description = self._network['description']
        self._vpc, self._vpc_name = self._add_vpc()
        self._add_dhcp()
        self._gateway = self._add_gateway()
        self._internet_gateway = self._add_gateway_attachment()
        self._route_table = self._add_route_table()
        self._add_public_route()
        self._acl = self._add_network_acl()
        self._add_network_acl_entries()


    def _add_vpc(self):
        """Add the VPC section to the template, returning the id and name
        for use in the other sections of the stack configuration

        :rtype: str, str

        """
        vpc_id = ''.join(x.capitalize() for x in self._environment.split('-'))
        vpc_name = self._environment.replace('-', '_')

        self.add_resource(vpc_id, _VPC(
            vpc_name, self._network['vpc']['dns-support'],
            self._network['vpc']['dns-hostnames'], self._network['cidr']))
        return vpc_id, vpc_name

    def _add_dhcp(self):
        """Add all of the DHCP options to the template for the given VPC"""
        self._add_dhcp_association(self._add_dhcp_options())

    def _add_dhcp_options(self):
        """Add all of the DHCP options to the template for the given VPC

        :rtype: str

        """
        config = self._network['dhcp-options']
        dhcp_id = '{0}Dhcp'.format(self._vpc)
        self.add_resource(dhcp_id, _DHCPOptions(config['domain-name'],
                                                config['name-servers'],
                                                config['ntp-servers']))
        return dhcp_id

    def _add_dhcp_association(self, dhcp_id):
        """Add all of the DHCP OptionsAssociation to the template for the given
        VPC and DHCP Options ID.

        :param str dhcp_id: The DHCP Options ID

        """
        self.add_resource('{0}Assoc'.format(dhcp_id),
                          _DHCPOptionsAssociation(dhcp_id, self._vpc))

    def _add_gateway(self):
        """Add a gateway to the template for the specified VPC

        :rtype: str

        """
        gateway = '{0}Gateway'.format(self._vpc)
        self.add_resource(gateway, _Gateway())
        return gateway

    def _add_gateway_attachment(self):
        """Attach the specified gateway to the VPC

        :rtype: str

        """
        internet_gateway_id = '{0}Attachment'.format(self._gateway)
        self.add_resource(internet_gateway_id,
                          _GatewayAttachment(self._vpc, self._gateway))
        return internet_gateway_id

    def _add_network_acl(self):
        """Add the Network ACL to the VPC

        :rtype: str

        """
        acl = '{0}Acl'.format(self._vpc)
        self.add_resource(acl, _NetworkACL(self._vpc_name, self._vpc))
        return acl

    def _add_network_acl_entries(self):
        """Iterate through the ACL entries and add them"""
        for index, acl in enumerate(self._network['network-acls']):
            self.add_resource('{0}{1}'.format(self._acl, index),
                              _NetworkACLEntry(self._acl, acl['cidr'],
                                               acl['number'], acl['protocol'],
                                               acl['action'], acl['egress'],
                                               acl['ports']))

    def _add_public_route(self):
        """Add the public route specified in the mapping ``pubic/cidr`` for
        the specified VPC, route table, gateway and internet gateway.

        """
        self.add_resource('{0}Route'.format(self._vpc),
                          _Route(self._route_table,
                                 {'Fn::FindInMap': ['SubnetConfig',
                                                    'Public',
                                                    'CIDR']},
                                 self._gateway, self._internet_gateway))

    def _add_route_table(self,):
        """Add the the route table for the specified VPC

        :rtype: str

        """
        route_table_id = '{0}RouteTable'.format(self._vpc)
        self.add_resource(route_table_id, _RouteTable(self._vpc))
        return route_table_id

    def _add_subnets(self):
        """Add the network subnets for the specified VPC and route table"""
        for subnet in self._network['subnets']:
            config = self._network['subnets'][subnet]
            subnet_id = '{0}{1}Subnet'.format(self._vpc, subnet)
            self.add_resource(subnet_id,
                              _Subnet(self._vpc_name, subnet, self._vpc,
                                      config['az'], config['cidr']))
            self.add_resource('{0}Assoc'.format(subnet_id),
                              _SubnetRouteTableAssociation(subnet_id,
                                                           self._route_table))

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
        self._properties['Egress'] = egress
        ports = ports.split('-') if ports else (0, 65536)
        port_range = {'From': ports[0], 'To': ports[1]}
        self._properties['PortRange'] = port_range
