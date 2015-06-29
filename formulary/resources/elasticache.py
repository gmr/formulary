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
    def __init__(self):
        super(CacheCluster, self).__init__('AWS::ElastiCache::CacheCluster')
        self._properties = {'AutoMinorVersionUpgrade': None,
                            'AZMode': '',
                            'CacheNodeType': '',
                            'CacheParameterGroupName': '',
                            'CacheSecurityGroupNames': [],
                            'CacheSubnetGroupName': '',
                            'ClusterName': '',
                            'Engine': '',
                            'EngineVersion': '',
                            'NotificationTopicArn': '',
                            'NumCacheNodes': '',
                            'Port': 11211,
                            'PreferredAvailabilityZone': '',
                            'PreferredAvailabilityZones': [],
                            'PreferredMaintenanceWindow': '',
                            'SnapshotArns': [],
                            'SnapshotName': '',
                            'SnapshotRetentionLimit': 0,
                            'SnapshotWindow': '',
                            'VpcSecurityGroupIds': ['']}
