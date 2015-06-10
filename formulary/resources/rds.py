"""
Cloud Formation RDS Resources

"""
from formulary import base


class DBInstance(base.Resource):
    def __init__(self, name, config, subnet, security_grp):
        super(DBInstance, self).__init__('AWS::RDS::DBInstance')
        self._name = name
        self._properties = {
            'AllocatedStorage': config.get('storage-capacity'),
            'AutoMinorVersionUpgrade': config.get('minor-version-upgrade',
                                                  False),
            'BackupRetentionPeriod': config.get('backup-retention'),
            'DBName': config.get('dbname'),
            'DBInstanceClass': config.get('instance-type'),
            'DBInstanceIdentifier': name,
            'DBSubnetGroupName': {'Ref': subnet},
            'Engine': config.get('engine'),
            'EngineVersion': config.get('engine-version'),
            'Iops': config.get('iops'),
            'MasterUsername': config.get('username'),
            'MasterUserPassword': config.get('password'),
            'MultiAZ': config.get('multi-az', True),
            'Port': config.get('port'),
            'PubliclyAccessible': config.get('public', False),
            'VPCSecurityGroups': [security_grp]
        }

        if not config.get('multi-az'):
            self._properties['AvailabilityZone'] =  \
                config.get('availability_zone')

        self.add_attribute('DeletionPolicy',
                           config.get('deletion-policy',
                                      'Delete').capitalize())


class DBSubnetGroup(base.Resource):
    def __init__(self, name, subnets):
        super(DBSubnetGroup, self).__init__('AWS::RDS::DBSubnetGroup')
        self._name = name
        self._properties = {
            'DBSubnetGroupDescription': 'Subnet Group for {0}'.format(name),
            'SubnetIds': subnets
        }
