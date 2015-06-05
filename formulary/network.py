"""
Cloud Formation Network Stack Management

"""
import collections

from boto import vpc

from formulary import cloudformation

Subnet = collections.namedtuple('Subnet', ['id',
                                           'availability_zone',
                                           'cidr_block',
                                           'environment',
                                           'status',
                                           'available_ips'])
VPC = collections.namedtuple('VPC', ['id',
                                     'cidr_block',
                                     'is_default',
                                     'instance_tenancy',
                                     'status'])


class NetworkStack(cloudformation.Stack):
    """Represents the an existing Formulary network Cloud Formation stack
    with attributes that return the AWS ids.

    """
    CONFIG_PREFIX = 'vpcs'

    def __init__(self, name, config_path, region='us-east-1'):
        """Create a new instance of a Stack for the given region and
        stack name.

        :param str name: The stack name
        :param str region: The AWS region, defaults to ``us-east-1``

        """
        super(NetworkStack, self).__init__(name, None, config_path, region)
        self._vpc_connection = vpc.VPCConnection()
        self._subnets = self._get_subnets(self._get_subnet_ids())
        self._vpc = self._get_vpc()
        self._config = self._load_config(self._local_path, 'network')

    @property
    def cidr_block(self):
        """Return the CIDR block for the VPC

        :rtype: str

        """
        return self._vpc.cidr_block

    @property
    def environment(self):
        """Returns the environment the stack is for.

        :rtype: str

        """
        return self._config.get('environment')

    @property
    def subnets(self):
        """Returns a list of subnets created by this stack

        :rtype: list

        """
        return self._subnets

    @property
    def vpc(self):
        return self._vpc

    def _get_subnet_ids(self):
        """Return the AWS physical ID list used to get the subnet details

        :rtype: list

        """
        values = []
        for resource in self._resources:
            if resource.type == 'AWS::EC2::Subnet':
                values.append(resource.id)
        return values

    def _get_subnets(self, subnet_ids):
        """Fetches subnet data from AWS for the given subnets, returning
        a list of namedtuples with additional subnet data.

        :param list subnet_ids: The list of subnet IDs from AWS
        :rtype: list

        """
        values = []
        subnets = self._vpc_connection.get_all_subnets(subnet_ids)
        for subnet in subnets:
            values.append(Subnet(subnet.id,
                                 subnet.availability_zone,
                                 subnet.cidr_block,
                                 subnet.tags.get('Environment'),
                                 subnet.state,
                                 subnet.available_ip_address_count))
        return sorted(values, key=lambda x: x.availability_zone)

    def _get_vpc(self):
        """Fetch the details of the VPC and return them as a namedtuple

        :rtype: VPC

        """
        for resource in self._resources:
            if resource.type == 'AWS::EC2::VPC':
                results = self._vpc_connection.get_all_vpcs(resource.id)
                return VPC(results[0].id,
                           results[0].cidr_block,
                           results[0].is_default,
                           results[0].instance_tenancy,
                           results[0].state)


class NetworkTemplate(cloudformation.Template):
    """Create a Network cloud-formation stack consisting of the VPC,
    DHCP options, gateway configuration, routing tables, subnets, and network
    ACLs.

    """
    CONFIG_PREFIX = 'vpcs'

    def __init__(self, name, environment, config_path, region=None):
        """Create a new instance of a network stack.

        :param str name: The environment name for the stack
        :param str config_path: Path to the formulary configuration directory

        """
        super(NetworkTemplate, self).__init__(name, None, config_path)
        self._network = self._load_config(self._local_path, 'network')
        self._description = self._network['description']
        self._vpc, self._vpc_name = self._add_vpc()
        self._add_dhcp()
        self._gateway = self._add_gateway()
        self._internet_gateway = self._add_gateway_attachment()
        self._route_table = self._add_route_table()
        self._add_public_route()
        self._acl = self._add_network_acl()
        self._add_network_acl_entries()
        self._add_subnets()

    def _add_vpc(self):
        """Add the VPC section to the template, returning the id and name
        for use in the other sections of the stack configuration

        :rtype: str, str

        """
        vpc_id = self._to_camel_case(self._name)
        vpc_name = self._name.replace('-', '_')
        resource = _VPC(vpc_name,
                        self._network['vpc']['dns-support'],
                        self._network['vpc']['dns-hostnames'],
                        self._network['CIDR'])
        resource.add_tag('Environment', self._network['environment'])
        self.add_resource(vpc_id, resource)
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
        resource = _NetworkACL(self._vpc_name, self._vpc)
        resource.add_tag('Environment', self._network['environment'])
        self.add_resource(acl, resource)
        return acl

    def _add_network_acl_entries(self):
        """Iterate through the ACL entries and add them"""
        for index, acl in enumerate(self._network['network-acls']):
            self.add_resource('{0}{1}'.format(self._acl, index),
                              _NetworkACLEntry(self._acl, acl['CIDR'],
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
        subnet_ids = []
        for subnet in self._network['subnets']:
            config = self._network['subnets'][subnet]
            subnet_id = '{0}{1}Subnet'.format(self._vpc, subnet)
            subnet_ids.append(subnet_id)
            resource = _Subnet(self._vpc_name, subnet, self._vpc,
                               config['availability_zone'], config['CIDR'])
            resource.add_tag('Environment', self._network['environment'])
            self.add_resource(subnet_id, resource)
            self.add_resource('{0}Assoc'.format(subnet_id),
                              _SubnetRouteTableAssociation(subnet_id,
                                                           self._route_table))


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
