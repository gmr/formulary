"""
Cloud Formation Resources

AWS::ElastiCache::CacheCluster
AWS::ElastiCache::ParameterGroup
AWS::ElastiCache::ReplicationGroup
AWS::ElastiCache::SecurityGroup
AWS::ElastiCache::SecurityGroupIngress
AWS::ElastiCache::SubnetGroup

"""
from formulary.resources import base


class CacheCluster(base.Resource):
    """The AWS::ElastiCache::CacheCluster type creates an Amazon ElastiCache
    cache cluster.

    """
    tags = False

    def __init__(self,
                 name,
                 minor_version_upgrade=True,
                 az_mode=None,
                 node_type='cache.r3.large',
                 parameter_group_name=None,
                 security_group_names=None,
                 subnet_group_name=None,
                 engine='memcached',
                 version='1.4.14',
                 node_qty=1,
                 notification_topic=None,
                 port=11211,
                 preferred_az=None,
                 preferred_azs=None,
                 preferred_maint_window=None,
                 snapshot_arns=None,
                 snapshot_name=None,
                 snapshot_retention_limit=None,
                 snapshot_window=None,
                 vpc_security_group_ids=None):
        super(CacheCluster, self).__init__('AWS::ElastiCache::CacheCluster')
        self._properties = {
            'AutoMinorVersionUpgrade': minor_version_upgrade,
            'AZMode': az_mode,
            'CacheNodeType': node_type,
            'CacheParameterGroupName': parameter_group_name,
            'CacheSecurityGroupNames': security_group_names,
            'CacheSubnetGroupName': subnet_group_name,
            'ClusterName': name[0:20],
            'Engine': engine,
            'EngineVersion': version,
            'NotificationTopicArn': notification_topic,
            'NumCacheNodes': node_qty,
            'Port': port,
            'PreferredAvailabilityZone': preferred_az,
            'PreferredAvailabilityZones': preferred_azs,
            'PreferredMaintenanceWindow': preferred_maint_window,
            'SnapshotArns': snapshot_arns,
            'SnapshotName': snapshot_name,
            'SnapshotRetentionLimit': snapshot_retention_limit,
            'SnapshotWindow': snapshot_window,
            'VpcSecurityGroupIds': vpc_security_group_ids}


class ParameterGroup(base.Resource):
    """The AWS::ElastiCache::ParameterGroup type creates a new cache parameter
    group. Cache parameter groups control the parameters for a cache cluster.

    """
    def __init__(self, family, description, properties):
        super(ParameterGroup,
              self).__init__('AWS::ElastiCache::ParameterGroup')
        self._properties = {'CacheParameterGroupFamily': family,
                            'Description': description,
                            'Properties': properties}


class ReplicationGroup(base.Resource):
    """The AWS::ElastiCache::ReplicationGroup resource creates an Amazon
    ElastiCache replication group. A replication group is a collection of cache
    clusters, where one of the clusters is a primary read-write cluster and the
    others are read-only replicas.

    .. note::

        Currently, replication groups are supported only for Redis clusters.

    """
    def __init__(self,
                 auto_failover=True,
                 auto_minor_version_upgrade=True,
                 node_type='cache.r3.large',
                 param_group_name=None,
                 security_group_name=None,
                 subnet_group_name=None,
                 engine='memcached',
                 version='1.4.14',
                 notification_topic=None,
                 num_clusters=2,
                 port=11211,
                 preferred_az=None,
                 preferred_maint_window=None,
                 description=None,
                 security_group_ids=None,
                 snapshot_arns=None,
                 snapshot_retention_limit=None,
                 snapshot_window=None):
        super(ReplicationGroup,
              self).__init__('AWS::ElastiCache::ReplicationGroup')
        self._properties = {
            'AutomaticFailoverEnabled': auto_failover,
            'AutoMinorVersionUpgrade': auto_minor_version_upgrade,
            'CacheNodeType': node_type,
            'CacheParameterGroupName': param_group_name,
            'CacheSecurityGroupNames': security_group_name,
            'CacheSubnetGroupName': subnet_group_name,
            'Engine': engine,
            'EngineVersion': version,
            'NotificationTopicArn': notification_topic,
            'NumCacheClusters': num_clusters,
            'Port': port,
            'PreferredCacheClusterAZs': preferred_az,
            'PreferredMaintenanceWindow': preferred_maint_window,
            'ReplicationGroupDescription': description,
            'SecurityGroupIds': security_group_ids,
            'SnapshotArns': snapshot_arns,
            'SnapshotRetentionLimit': snapshot_retention_limit,
            'SnapshotWindow': snapshot_window}


class SecurityGroup(base.Resource):
    """The AWS::ElastiCache::SecurityGroup resource creates a cache security
    group. For more information about cache security groups, go to Cache
    Security Groups in the Amazon ElastiCache User Guide or go to
    CreateCacheSecurityGroup in the Amazon ElastiCache API Reference Guide.

    To create an ElastiCache cluster in a VPC, use the AWS::EC2::SecurityGroup
    resource. For more information, see the VpcSecurityGroupIds property in the
    AWS::ElastiCache::CacheCluster resource.

    """
    def __init__(self, description):
        super(SecurityGroup,
              self).__init__('AWS::ElastiCache::SecurityGroup')
        self._properties['Description'] = description


class SecurityGroupIngress(base.Resource):
    """The AWS::ElastiCache::SecurityGroupIngress type authorizes ingress to a
    cache security group from hosts in specified Amazon EC2 security groups.
    For more information about ElastiCache security group ingress, go to
    AuthorizeCacheSecurityGroupIngress in the Amazon ElastiCache API Reference
    Guide.

    """
    def __init__(self, security_group_name,
                 ec2_group_name=None, ec2_group_owner_id=None):
        super(SecurityGroupIngress,
              self).__init__('AWS::ElastiCache::SecurityGroupIngress')
        self._properties = {'CacheSecurityGroupName': security_group_name,
                            'EC2SecurityGroupName': ec2_group_name,
                            'EC2SecurityGroupOwnerId': ec2_group_owner_id}


class SubnetGroup(base.Resource):
    """Creates a cache subnet group. For more information about cache subnet
    groups, go to Cache Subnet Groups in the Amazon ElastiCache User Guide or
    go to CreateCacheSubnetGroup in the Amazon ElastiCache API Reference Guide.

    """
    def __init__(self, description, subnet_ids):
        super(SubnetGroup,
              self).__init__('AWS::ElastiCache::SubnetGroup')
        self._properties = {'Description': description,
                            'SubnetIds': subnet_ids}
