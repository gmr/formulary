"""
Cloud Formation Port 53 Resources

"""
from formulary import base


class Route53AliasTarget(base.Property):
    def __init__(self, dns_name, hosted_zone_id, eval_target_health=False):
        super(Route53AliasTarget, self).__init__()
        self._values = {'DNSName': dns_name,
                        'HostedZoneId': hosted_zone_id,
                        'EvaluateTargetHealth': eval_target_health}


class Route53HostedZone(base.Resource):

    tags = False

    def __init__(self, config, tags, name, vpcs):
        super(Route53HostedZone, self).__init__('AWS::Route53::HostedZone')
        self._properties['HostedZoneConfig'] = config
        self._properties['HostedZoneTags'] = tags
        self._properties['Name'] = name
        self._properties['VPCs'] = vpcs


class Route53HostedZoneConfig(base.Property):
    def __init__(self, comment):
        super(Route53HostedZoneConfig, self).__init__()
        self._values = {'Comment': comment}


class Route53HostedZoneTags(base.Property):
    def __init__(self, tags):
        super(Route53HostedZoneTags, self).__init__()
        self._values = [{'Key': k, 'Value': v} for k,v in tags]


class Route53HostedZoneVPCs(base.Property):
    def __init__(self, vpcs):
        super(Route53HostedZoneVPCs, self).__init__()
        self._values = [{'VPCId': k, 'VPCRegion': v} for k,v in vpcs]


class Route53RecordSet(base.Resource):

    tags = False

    def __init__(self, domain_name, hostname, resources=None,
                 alias_target=None, record_type='A', ttl=300, comment=None):
        super(Route53RecordSet, self).__init__('AWS::Route53::RecordSet')
        if alias_target and resources:
            raise ValueError('Can not have both resources and an alias target')
        if alias_target and ttl:
            ttl = None
        if not alias_target and not resources:
            raise ValueError('Must have either an alias target or resources')
        domain_name = domain_name.rstrip('.') + '.'
        self._properties['Comment'] = comment
        self._properties['AliasTarget'] = alias_target
        self._properties['Failover'] = None
        self._properties['GeoLocation'] = None
        self._properties['HealthCheckId'] = None
        self._properties['HostedZoneName'] = domain_name
        self._properties['Name'] = '{0}.{1}'.format(hostname, domain_name)
        self._properties['Region'] = None
        self._properties['ResourceRecords'] = resources
        self._properties['SetIdentifier'] = None
        self._properties['TTL'] = str(ttl) if ttl else None
        self._properties['Type'] = record_type
        self._properties['Weight'] = None


class Route53RecordSetGroup(base.Resource):

    tags = False

    def __init__(self, domain_name, record_sets, comment=None):
        super(Route53RecordSetGroup,
              self).__init__('AWS::Route53::RecordSetGroup')
        self._properties['Comment'] = comment
        self._properties['HostedZoneName'] = domain_name
        self._properties['RecordSets'] = record_sets
