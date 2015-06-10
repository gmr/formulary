"""
namedtuple representations of Stack resources

"""
from collections import namedtuple

DHCPOptions = namedtuple('DHCPOptions', ['id', 'logical_id', 'timestamp',
                                         'status', 'domain_name',
                                         'dns_servers', 'ntp_servers', 'tags'])

DHCPOptionsAssociation = namedtuple('DHCPOptionsAssociation',
                                    ['id', 'logical_id', 'timestamp',
                                     'status'])

GatewayAssociation = namedtuple('GatewayAssociation',
                                ['id', 'logical_id', 'timestamp', 'status'])


InternetGateway = namedtuple('InternetGateway',
                             ['id', 'logical_id', 'timestamp', 'status'])

NetworkACL = namedtuple('NetworkACL', ['id', 'logical_id', 'timestamp',
                                       'status', 'entries', 'tags'])

NetworkACLEntry = namedtuple('NetworkACLEntry', ['logical_id', 'timestamp',
                                                 'status', 'number',
                                                 'cidr_block', 'egress',
                                                 'action', 'protocol',
                                                 'from_port', 'to_port'])

Route = namedtuple('Route', ['id', 'logical_id', 'timestamp', 'status'])

RouteTable = namedtuple('RouteTable', ['id', 'logical_id', 'timestamp',
                                       'status', 'associations', 'tags'])

Subnet = namedtuple('Subnet', ['id',  'logical_id', 'timestamp', 'status',
                               'availability_zone', 'cidr_block',
                               'available_ips'])

SubnetRouteTableAssociation = namedtuple('SubnetRouteTableAssociation',
                                         ['id', 'logical_id', 'timestamp',
                                          'status'])

VPC = namedtuple('VPC', ['id', 'logical_id', 'timestamp', 'status',
                         'description', 'cidr_block', 'is_default',
                         'instance_tenancy', 'dhcp_options_id', 'tags'])
