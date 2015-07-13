"""
Cloud Formation ELB Resources

AWS::ElasticLoadBalancing::LoadBalancer

"""
from formulary.resources import base


class AccessLoggingPolicy(base.Property):
    """The AccessLoggingPolicy property describes where and how access logs are
    stored for the AWS::ElasticLoadBalancing::LoadBalancer resource.

    """
    def __init__(self, emit_interval, enabled, s3_bucket, s3_prefix):
        super(AccessLoggingPolicy, self).__init__()
        self._values = {'EmitInterval': emit_interval,
                        'Enabled': enabled,
                        'S3BucketName': s3_bucket,
                        'S3BucketPrefix': s3_prefix}


class AppCookieStickinessPolicy(base.Property):
    """The AppCookieStickinessPolicy type is an embedded property of the
    AWS::ElasticLoadBalancing::LoadBalancer type.

    """
    def __init__(self, cookie_name, policy_name):
        super(AppCookieStickinessPolicy, self).__init__()
        self._values = {'CookieName': cookie_name,
                        'PolicyName': policy_name}


class ConnectionDrainingPolicy(base.Property):
    """The ConnectionDrainingPolicy property describes how deregistered or
    unhealthy instances handle in-flight requests for the
    AWS::ElasticLoadBalancing::LoadBalancer resource. Connection draining
    ensures that the load balancer completes serving all in-flight requests
    made to a registered instance when the instance is deregistered or becomes
    unhealthy. Without connection draining, the load balancer closes
    connections to deregistered or unhealthy instances, and any in-flight
    requests are not completed.

    """
    def __init__(self, enabled, timeout):
        super(ConnectionDrainingPolicy, self).__init__()
        self._values = {'Enabled': enabled, 'Timeout': timeout}


class ConnectionSettings(base.Property):
    """ConnectionSettings is a property of the
    AWS::ElasticLoadBalancing::LoadBalancer resource that describes how long
    the front-end and back-end connections of your load balancer can remain
    idle.

    """
    def __init__(self, idle_timeout):
        super(ConnectionSettings, self).__init__()
        self._values = {'IdleTimeout': idle_timeout}


class HeathCheck(base.Property):
    """The ElasticLoadBalancing HealthCheck is an embedded property of the
    AWS::ElasticLoadBalancing::LoadBalancer type.

    """
    def __init__(self, interval=30, target='HTTP:80', timeout=5,
                 healthy=2, unhealthy=2):
        super(HeathCheck, self).__init__()
        self._values = {'HealthyThreshold': healthy,
                        'Interval': interval,
                        'Target': target,
                        'Timeout': timeout,
                        'UnhealthyThreshold': unhealthy}


class LBCookieStickinessPolicy(base.Property):
    """The LBCookieStickinessPolicy type is an embedded property of the
    AWS::ElasticLoadBalancing::LoadBalancer type.

    """
    def __init__(self, expiration_period, policy_name):
        super(LBCookieStickinessPolicy, self).__init__()
        self._values = {'CookieExpirationPeriod': expiration_period,
                        'PolicyName': policy_name}


class Listener(base.Property):
    """The Listener property is an embedded property of the
    AWS::ElasticLoadBalancing::LoadBalancer type.

    """
    def __init__(self, port, protocol, instance_port, instance_protocol,
                 policy_names=None, ssl_certificate_id=None):
        super(Listener, self).__init__()
        self._values = {'InstancePort': instance_port,
                        'InstanceProtocol': instance_protocol,
                        'LoadBalancerPort': port,
                        'PolicyNames':  policy_names or [],
                        'Protocol': protocol,
                        'SSLCertificateId': ssl_certificate_id}


class LoadBalancer(base.Resource):
    """The AWS::ElasticLoadBalancing::LoadBalancer type creates a LoadBalancer.

    """
    def __init__(self, name, instances, health_check, listeners,
                 security_groups, subnets,
                 availability_zone=None,
                 policies=None, cross_zone=False, internal=False):
        super(LoadBalancer,
              self).__init__('AWS::ElasticLoadBalancing::LoadBalancer')
        scheme = 'internal' if internal else 'internet-facing'
        self._properties = {'AvailabilityZone': availability_zone,
                            'CrossZone': cross_zone,
                            'HealthCheck': health_check.as_dict(),
                            'LoadBalancerName': name,
                            'Instances': instances,
                            'Listeners': [l.as_dict() for l in listeners],
                            'Policies': policies,
                            'Scheme': scheme,
                            'SecurityGroups': security_groups,
                            'Subnets': subnets}


class Policy(base.Property):
    """The ElasticLoadBalancing policy type is an embedded property of the
    AWS::ElasticLoadBalancing::LoadBalancer resource. You associate policies
    with a listener by referencing a policy's name in the listener's
    PolicyNames property.

    """
    def __init__(self, attributes, instance_ports, load_balancer_ports,
                 policy_name, policy_type):
        super(Policy, self).__init__()
        self._values = {'Attributes': attributes,
                        'InstancePorts': instance_ports,
                        'LoadBalancerPorts': load_balancer_ports,
                        'PolicyName': policy_name,
                        'PolicyType': policy_type}
