"""
Cloud Formation ELB Resources

"""
from formulary import base


class ELB(base.Resource):
    def __init__(self, name, instances, health_check, listeners,
                 security_groups, subnets, policies=None, cross_zone=False,
                 internal=False):
        super(ELB, self).__init__('AWS::ElasticLoadBalancing::LoadBalancer')
        self._properties = {
            'CrossZone': cross_zone,
            'HealthCheck': health_check.as_dict(),
            'LoadBalancerName': name,
            'Instances': instances,
            'Listeners': [l.as_dict() for l in listeners],
            'Policies': policies,
            'Scheme': 'internal' if internal else 'internet-facing',
            'SecurityGroups': security_groups,
            'Subnets': subnets
        }


class ELBHeathCheck(base.Property):

    def __init__(self, interval=30, target='HTTP:80', timeout=5,
                 healthy=10, unhealthy=2):
        super(ELBHeathCheck, self).__init__()
        self._values = {
            'HealthyThreshold': healthy,
            'Interval': interval,
            'Target': target,
            'Timeout': timeout,
            'UnhealthyThreshold': unhealthy
        }


class ELBListener(base.Property):
    def __init__(self, port, protocol, instance_port, instance_protocol,
                 policy_names=None, ssl_certificate_id=None):
        super(ELBListener, self).__init__()
        self._values = {'InstancePort': instance_port,
                        'InstanceProtocol': instance_protocol,
                        'LoadBalancerPort': port,
                        'PolicyNames':  policy_names or [],
                        'Protocol': protocol,
                        'SSLCertificateId': ssl_certificate_id}


