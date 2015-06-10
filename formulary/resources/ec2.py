"""
Cloud Formation EC2 Resources

"""
from formulary import base


class EC2BlockDevice(base.Property):
    def __init__(self, name, ebs, no_device=None, virtual_name=None):
        super(EC2BlockDevice, self).__init__()
        self._values = {'DeviceName': name,
                        'Ebs': ebs,
                        'NoDevice': no_device or {},
                        'VirtualName': virtual_name}


class EC2Instance(base.Resource):
    def __init__(self, name, ami, availability_zone, instance_type, subnet,
                 security_group, user_data, storage_size=20, private_ip=None):
        super(EC2Instance, self).__init__('AWS::EC2::Instance')
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
        volume = {
            'DeviceName': '/dev/xvda',
            'Ebs': {'VolumeType': 'gp2',
                    'VolumeSize': storage_size}
        }
        self._properties = {
            'AvailabilityZone': availability_zone,
            'BlockDeviceMappings': [volume],
            'DisableApiTermination': False,
            'EbsOptimized': False,
            'ImageId': ami,
            'InstanceInitiatedShutdownBehavior': 'stop',
            'InstanceType': instance_type,
            'KeyName': {'Fn::FindInMap': ['AWS', 'KeyName', 'Value']},
            'Monitoring': False,
            'NetworkInterfaces': [nic],
            'UserData': user_data
        }

    @property
    def subnet(self):
        return self._subnet


class SecurityGroup(base.Resource):
    def __init__(self, name, description, vpc, ingress):
        super(SecurityGroup, self).__init__('AWS::EC2::SecurityGroup')
        self._name = name
        self._properties['GroupDescription'] = description
        self._properties['SecurityGroupIngress'] = ingress
        self._properties['VpcId'] = vpc



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

