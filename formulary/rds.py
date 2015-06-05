"""
For creating RDS instance stacks

"""
from os import path

from formulary import cloudformation
from formulary import security_group

DEFAULT_BACKUP_RETENTION = 3
DEFAULT_INSTANCE_TYPE = 'db.t2.small'
DEFAULT_ENGINE_TYPE = 'postgres'
DEFAULT_ENGINE_VERSION = '9.4.1'
DEFAULT_ENGINE_PORT = 5432
DEFAULT_STORAGE_CAPACITY = 100
DEFAULT_IOPS = 1000


class RDSTemplate(security_group.TemplateWithSecurityGroup):

    CONFIG_PREFIX = 'rds'
    PARENT_CONFIG_PREFIX = 'vpcs'
    STACK_TYPE = 'RDS'

    def __init__(self, name, parent, config_path, region='us-east-1'):
        super(RDSTemplate, self).__init__(name, parent, config_path, region)
        self._config = self._load_config(self._local_path, name)
        self._init_network_stack()
        self._security_group = self._add_security_group()
        self._add_instance()
        if self._config.get('description'):
            self.set_description(self._config.get('description'))

    def _add_instance(self):
        config = self._flatten_config(self._config)
        subnets = self._add_subnet_groups(config)
        if not config.get('multi-az'):
            config['availability_zone'] = \
                self._network_stack.subnets[0].availability_zone
        resource = _DBInstance(self.name, config, subnets, self._security_group)
        self._add_environment_tag(resource)
        self.add_resource(self._to_camel_case(self._name), resource)

    def _add_subnet_groups(self, config):
        subnets = []
        if config.get('multi-az'):
            subnets.append(self._network_stack.subnets[0].id)
        else:
            for subnet in self._network_stack.subnets:
                subnets.append(subnet.id)
        subnet_group_name = '{0}-subnet-group'.format(self.name)
        resource = _DBSubnetGroup(subnet_group_name, subnets)
        self._add_environment_tag(resource)
        subnet_group_name = self._to_camel_case(subnet_group_name)
        self.add_resource(subnet_group_name, resource)
        return subnet_group_name

    @property
    def _local_path(self):
        """Return a path to the config file local to the Template type being
        created.

        :rtype: str

        """
        return path.join(self._config_path, self.CONFIG_PREFIX)


class _DBInstance(cloudformation.Resource):
    def __init__(self, name, config, subnet, security_grp):
        super(_DBInstance, self).__init__('AWS::RDS::DBInstance')
        self._name = name
        self._properties = {
            'AllocatedStorage': config.get('storage-capacity',
                                           DEFAULT_STORAGE_CAPACITY),
            'AutoMinorVersionUpgrade': config.get('minor-version-upgrade',
                                                  False),
            'BackupRetentionPeriod': config.get('backup-retention',
                                                DEFAULT_BACKUP_RETENTION),
            'DBName': config.get('dbname'),
            'DBInstanceClass': config.get('instance-type',
                                          DEFAULT_INSTANCE_TYPE),
            'DBInstanceIdentifier': name,
            'DBSubnetGroupName': {'Ref': subnet},
            'Engine': config.get('engine', DEFAULT_ENGINE_TYPE),
            'EngineVersion': config.get('engine-version',
                                        DEFAULT_ENGINE_VERSION),
            'Iops': config.get('iops'),
            'MasterUsername': config.get('username'),
            'MasterUserPassword': config.get('password'),
            'MultiAZ': config.get('multi-az', True),
            'Port': config.get('port', DEFAULT_ENGINE_PORT),
            'PubliclyAccessible': config.get('public', False),
            'VPCSecurityGroups': [security_grp]
        }

        if not config.get('multi-az'):
            self._properties['AvailabilityZone'] = \
                config.get('availability_zone')

        self.add_attribute('DeletionPolicy',
                           config.get('deletion-policy', 'Delete').capitalize())


class _DBSubnetGroup(cloudformation.Resource):
    def __init__(self, name, subnets):
        super(_DBSubnetGroup, self).__init__('AWS::RDS::DBSubnetGroup')
        self._name = name
        self._properties = {
            'DBSubnetGroupDescription': 'Subnet Group for {0}'.format(name),
            'SubnetIds': subnets
        }
