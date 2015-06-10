"""
Cloud Formation VPC Resources

"""
from formulary import base
from formulary import utils


class DHCPOptions(base.Resource):
    def __init__(self, domain_name, name_servers, ntp_servers):
        super(DHCPOptions, self).__init__('AWS::EC2::DHCPOptions')
        self._properties['DomainName'] = domain_name
        self._properties['DomainNameServers'] = name_servers
        self._properties['NtpServers'] = ntp_servers


class DHCPOptionsAssociation(base.Resource):
    def __init__(self, dhcp_id, vpc_id):
        super(DHCPOptionsAssociation,
              self).__init__('AWS::EC2::VPCDHCPOptionsAssociation')
        self._properties['DhcpOptionsId'] = {'Ref': dhcp_id}
        self._properties['VpcId'] = {'Ref': vpc_id}


class Gateway(base.Resource):
    def __init__(self):
        super(Gateway, self).__init__('AWS::EC2::InternetGateway')


class GatewayAttachment(base.Resource):
    def __init__(self, vpc_id, gateway_id):
        super(GatewayAttachment,
              self).__init__('AWS::EC2::VPCGatewayAttachment')
        self._properties['InternetGatewayId'] = {'Ref': gateway_id}
        self._properties['VpcId'] = {'Ref': vpc_id}


class NetworkACL(base.Resource):
    def __init__(self, vpc_name, vpc_id):
        super(NetworkACL, self).__init__('AWS::EC2::NetworkAcl')
        self._name = '{0}-acl'.format(vpc_name)
        self._properties['VpcId'] = {'Ref': vpc_id}


class NetworkACLEntry(base.Resource):
    def __init__(self, acl_id, cidr_block, rule_number, action, egress, ports):
        super(NetworkACLEntry, self).__init__('AWS::EC2::NetworkAclEntry')
        protocol, from_port, to_port = utils.parse_port_value(ports, -1)
        self._properties['NetworkAclId'] = {'Ref': acl_id}
        self._properties['CidrBlock'] = cidr_block
        self._properties['RuleNumber'] = rule_number
        self._properties['Protocol'] = protocol
        self._properties['RuleAction'] = action
        self._properties['Egress'] = egress
        self._properties['PortRange'] = {'From': from_port, 'To': to_port}


class Route(base.Resource):
    def __init__(self, route_table_id, cidr_block, gateway_id, depends_on):
        super(Route, self).__init__('AWS::EC2::Route')
        self._properties['RouteTableId'] = {'Ref': route_table_id}
        self._properties['DestinationCidrBlock'] = cidr_block
        self._properties['GatewayId'] = {'Ref': gateway_id}
        self._attributes['DependsOn'] = depends_on


class RouteTable(base.Resource):
    def __init__(self, vpc_id):
        super(RouteTable, self).__init__('AWS::EC2::RouteTable')
        self._properties['VpcId'] = {'Ref': vpc_id}


class Subnet(base.Resource):
    def __init__(self, vpc_name, subnet, vpc_id, az, cidr_block):
        super(Subnet, self).__init__('AWS::EC2::Subnet')
        self._name = '{0}{1}-subnet'.format(vpc_name, subnet)
        self._properties['AvailabilityZone'] = az
        self._properties['CidrBlock'] = cidr_block
        self._properties['VpcId'] = {'Ref': vpc_id}


class SubnetRouteTableAssociation(base.Resource):
    def __init__(self, subnet_id, route_table_id):
        super(SubnetRouteTableAssociation,
              self).__init__('AWS::EC2::SubnetRouteTableAssociation')
        self._properties['SubnetId'] = {'Ref': subnet_id}
        self._properties['RouteTableId'] = {'Ref': route_table_id}


class VPC(base.Resource):
    def __init__(self, name, dns_support, dns_hostnames, cidr_block):
        super(VPC, self).__init__('AWS::EC2::VPC')
        self._name = name
        self._properties['EnableDnsSupport'] = dns_support
        self._properties['EnableDnsHostnames'] = dns_hostnames
        self._properties['CidrBlock'] = cidr_block
