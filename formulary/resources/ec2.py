"""
Cloud Formation EC2 Resources

AWS::EC2::DHCPOptions
AWS::EC2::EIP
AWS::EC2::Instance
AWS::EC2::InternetGateway
AWS::EC2::NetworkAcl
AWS::EC2::NetworkAclEntry
AWS::EC2::Route
AWS::EC2::RouteTable
AWS::EC2::SecurityGroup
AWS::EC2::Subnet
AWS::EC2::SubnetNetworkAclAssociation
AWS::EC2::SubnetRouteTableAssociation
AWS::EC2::Volume
AWS::EC2::VolumeAttachment
AWS::EC2::VPC
AWS::EC2::VPCDHCPOptionsAssociation
AWS::EC2::VPCGatewayAttachment

"""
from formulary.resources import base
from formulary import utils


class BlockDevice(base.Property):
    """The Amazon EC2 block device mapping property is an embedded property of
    the AWS::EC2::Instance resource.

    """
    def __init__(self, name, ebs=None, no_device=None, virtual_name=None):
        super(BlockDevice, self).__init__()
        self._values = {'DeviceName': name,
                        'Ebs': ebs,
                        'NoDevice': no_device or {},
                        'VirtualName': virtual_name}


class EIP(base.Resource):
    """The AWS::EC2::EIP resource allocates an Elastic IP (EIP) address and
    can, optionally, associate it with an Amazon EC2 instance.

    """
    def __init__(self, instance_id):
        super(EIP, self).__init__('AWS::EC2::EIP')
        self._properties['InstanceId'] = instance_id
        self._properties['Domain'] = 'vpc'


class DHCPOptions(base.Resource):
    """Creates a set of DHCP options for your VPC."""
    def __init__(self, domain_name, name_servers, ntp_servers):
        super(DHCPOptions, self).__init__('AWS::EC2::DHCPOptions')
        self._properties['DomainName'] = domain_name
        self._properties['DomainNameServers'] = name_servers
        self._properties['NtpServers'] = ntp_servers


class Instance(base.CPResource):
    """The AWS::EC2::Instance type creates an Amazon EC2 instance."""
    def __init__(self, name, ami, availability_zone, block_devices,
                 instance_type, subnet, security_group, user_data,
                 private_ip=None, ebs=True, dependency=None):
        super(Instance, self).__init__('AWS::EC2::Instance')
        self._name = name
        self._subnet = subnet
        nic = {
            'AssociatePublicIpAddress': True,
            'DeviceIndex': '0',
            'GroupSet': [security_group],
            'SubnetId': subnet
        }
        if private_ip:
            nic['PrivateIpAddress'] = private_ip
        self._properties = {
            'AvailabilityZone': availability_zone,
            'BlockDeviceMappings': block_devices,
            'DisableApiTermination': False,
            'EbsOptimized': False,
            'ImageId': ami,
            'InstanceType': instance_type,
            'KeyName': {'Fn::FindInMap': ['AWS', 'KeyName', 'Value']},
            'Monitoring': False,
            'NetworkInterfaces': [nic],
            'UserData': user_data}
        if ebs:
            self._properties['InstanceInitiatedShutdownBehavior'] = 'stop'
        if dependency:
            self.set_dependency({"Ref": dependency})

    @property
    def subnet(self):
        return self._subnet


class InternetGateway(base.Resource):
    def __init__(self):
        super(InternetGateway, self).__init__('AWS::EC2::InternetGateway')


class MountPoint(base.Property):
    """The EC2 MountPoint property is an embedded property of the
    AWS::EC2::Instance type.

    """
    def __init__(self, device, volume_id):
        super(MountPoint, self).__init__()
        self._values = {'Device': device, 'VolumeId': volume_id}


class NetworkACL(base.Resource):
    def __init__(self, vpc_name, vpc_id):
        super(NetworkACL, self).__init__('AWS::EC2::NetworkAcl')
        self._name = '{0}-acl'.format(vpc_name)
        self._properties['VpcId'] = vpc_id


class NetworkACLEntry(base.Resource):
    def __init__(self, acl_id, cidr_block, rule_number, action, egress, ports):
        super(NetworkACLEntry, self).__init__('AWS::EC2::NetworkAclEntry')
        protocol, from_port, to_port = utils.parse_port_value(ports, -1)
        self._properties['NetworkAclId'] = acl_id
        self._properties['CidrBlock'] = cidr_block
        self._properties['RuleNumber'] = rule_number
        self._properties['Protocol'] = protocol
        self._properties['RuleAction'] = action
        self._properties['Egress'] = egress
        self._properties['PortRange'] = {'From': from_port, 'To': to_port}


class Route(base.Resource):
    def __init__(self, route_table_id, cidr_block, gateway_id, depends_on):
        super(Route, self).__init__('AWS::EC2::Route')
        self._properties['RouteTableId'] = route_table_id
        self._properties['DestinationCidrBlock'] = cidr_block
        self._properties['GatewayId'] = gateway_id
        self._attributes['DependsOn'] = depends_on


class RouteTable(base.Resource):
    def __init__(self, vpc_id):
        super(RouteTable, self).__init__('AWS::EC2::RouteTable')
        self._properties['VpcId'] = vpc_id


class SecurityGroup(base.Resource):
    """Creates an Amazon EC2 security group"""

    def __init__(self, name, description, vpc, ingress):
        super(SecurityGroup, self).__init__('AWS::EC2::SecurityGroup')
        self._name = name
        self._properties['GroupDescription'] = description
        self._properties['SecurityGroupIngress'] = ingress
        self._properties['VpcId'] = vpc


class SecurityGroupIngress(base.Resource):
    """The AWS::EC2::SecurityGroupIngress resource adds an ingress rule to an
    Amazon EC2 or Amazon VPC security group.

    """
    tags = False

    def __init__(self, group_id, ip_protocol, from_port, to_port,
                 cidr=None, source_security_group_id=None):
        super(SecurityGroupIngress,
              self).__init__('AWS::EC2::SecurityGroupIngress')
        self._properties['GroupId'] = group_id
        self._properties['IpProtocol'] = ip_protocol
        self._properties['FromPort'] = from_port
        self._properties['ToPort'] = to_port
        self._properties['SourceSecurityGroupId'] = source_security_group_id
        self._properties['CidrIp'] = cidr


class SecurityGroupRule(base.Property):
    def __init__(self, protocol, from_port,
                 to_port=None,
                 cidr_addr=None,
                 source_id=None,
                 source_name=None,
                 source_owner=None):
        super(SecurityGroupRule, self).__init__()
        self._values = {'CidrIp': cidr_addr,
                        'FromPort': from_port,
                        'IpProtocol': protocol,
                        'SourceSecurityGroupId': source_id,
                        'SourceSecurityGroupName': source_name,
                        'SourceSecurityGroupOwnerId': source_owner,
                        'ToPort': to_port or from_port}


class Subnet(base.Resource):
    """Creates a subnet in an existing VPC."""
    def __init__(self, vpc_name, subnet, vpc_id, az, cidr_block):
        super(Subnet, self).__init__('AWS::EC2::Subnet')
        self._name = '{0}{1}-subnet'.format(vpc_name, subnet)
        self._properties['AvailabilityZone'] = az
        self._properties['CidrBlock'] = cidr_block
        self._properties['VpcId'] = vpc_id


class SubnetNetworkAclAssociation(base.Resource):
    """Associates a subnet with a network ACL."""
    def __init__(self, subnet_id, network_acl_id):
        super(SubnetNetworkAclAssociation,
              self).__init__('AWS::EC2::SubnetNetworkAclAssociation')
        self._properties['SubnetId'] = subnet_id
        self._properties['NetworkAclId'] = network_acl_id


class SubnetRouteTableAssociation(base.Resource):
    """Associates a subnet with a route table."""
    def __init__(self, subnet_id, route_table_id):
        super(SubnetRouteTableAssociation,
              self).__init__('AWS::EC2::SubnetRouteTableAssociation')
        self._properties['SubnetId'] = subnet_id
        self._properties['RouteTableId'] = route_table_id


class Volume(base.Resource):
    """The AWS::EC2::Volume type creates a new Amazon Elastic Block Store
    volume.

    """
    def __init__(self, availability_zone, iops, size,
                 tags=None, volume_type=None, encrypted=False, key_id=None,
                 snapshot_id=None):
        super(Volume, self).__init__('AWS::EC2::Volume')
        if encrypted and not key_id:
            raise ValueError('key_id must be set if encryption is enabled')
        self._properties['AvailabilityZone'] = availability_zone
        self._properties['Iops'] = iops
        self._properties['Size'] = size
        self._properties['KmsKeyId'] = key_id,
        self._properties['Encrypted'] = encrypted
        self._properties['SnapshotId'] = snapshot_id
        self._properties['Tags'] = tags
        self._properties['VolumeType'] = volume_type


class VolumeAttachment(base.Resource):
    """Attaches an Amazon EBS volume to a running instance and exposes it to
    the instance with the specified device name.

    """
    def __init__(self, device, instance_id, volume_id):
        super(VolumeAttachment, self).__init__('AWS::EC2::VolumeAttachment')
        self._properties['Device'] = device
        self._properties['InstanceId'] = instance_id
        self._properties['VolumeId'] = volume_id


class VPC(base.Resource):
    """Creates a Virtual Private Cloud (VPC) with the CIDR block that you
    specify.

    """
    def __init__(self, name, dns_support, dns_hostnames, cidr_block):
        super(VPC, self).__init__('AWS::EC2::VPC')
        self._name = name
        self._properties['EnableDnsSupport'] = dns_support
        self._properties['EnableDnsHostnames'] = dns_hostnames
        self._properties['CidrBlock'] = cidr_block


class VPCDHCPOptionsAssociation(base.Resource):
    """Associates a set of DHCP options (that you've previously created) with
    the specified VPC.

    """
    def __init__(self, dhcp_id, vpc_id):
        super(VPCDHCPOptionsAssociation,
              self).__init__('AWS::EC2::VPCDHCPOptionsAssociation')
        self._properties = {'DhcpOptionsId': dhcp_id, 'VpcId': vpc_id}


class VPCGatewayAttachment(base.Resource):
    """Attaches a gateway to a VPC."""
    def __init__(self, gateway_id, vpc_id):
        super(VPCGatewayAttachment,
              self).__init__('AWS::EC2::VPCGatewayAttachment')
        self._properties = {'InternetGatewayId': gateway_id, 'VpcId': vpc_id}
