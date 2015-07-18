"""
Cloud Formation Auto-Scaling Resources

AWS::AutoScaling::AutoScalingGroup
AWS::AutoScaling::LaunchConfiguration
AWS::AutoScaling::LifecycleHook
AWS::AutoScaling::ScalingPolicy
AWS::AutoScaling::ScheduledAction

"""
from formulary.resources import base


class AutoScalingGroup(base.Resource):
    """The AWS::AutoScaling::AutoScalingGroup type creates an Auto Scaling
    group.

    """
    def __init__(self, name):
        super(AutoScalingGroup,
              self).__init__('AWS::AutoScaling::AutoScalingGroup')
        self._name = name
        self._properties = {'AvailabilityZones': [],
                            'Cooldown': None,
                            'DesiredCapacity': None,
                            'HealthCheckGracePeriod': None,
                            'HealthCheckType': None,
                            'InstanceId': None,
                            'LaunchConfigurationName': None,
                            'LoadBalancerNames': [],
                            'MaxSize': None,
                            'MetricsCollection': [],
                            'MinSize': None,
                            'NotificationConfigurations': [],
                            'PlacementGroup': None,
                            'TerminationPolicies': [],
                            'VPCZoneIdentifier': []}


class LaunchConfiguration(base.Resource):
    """The AWS::AutoScaling::LaunchConfiguration type creates an Auto Scaling
    launch configuration that can be used by an Auto Scaling group to configure
    Amazon EC2 instances in the Auto Scaling group.

    """
    def __init__(self, name):
        super(LaunchConfiguration,
              self).__init__('AWS::AutoScaling::LaunchConfiguration')
        self._name = name
        self._properties = {'AssociatePublicIpAddress': False,
                            'BlockDeviceMappings': [],
                            'ClassicLinkVPCId': None,
                            'ClassicLinkVPCSecurityGroups': [],
                            'EbsOptimized': True,
                            'IamInstanceProfile': None,
                            'ImageId': None,
                            'InstanceId': None,
                            'InstanceMonitoring': False,
                            'InstanceType': None,
                            'KernelId': None,
                            'KeyName': None,
                            'PlacementTenancy': None,
                            'RamDiskId': None,
                            'SecurityGroups': [],
                            'SpotPrice': None,
                            'UserData': None}


class LifecycleHook(base.Resource):
    """Use AWS::AutoScaling::LifecycleHook to control the state of an instance
    in an Auto Scaling group after it is launched or terminated. When you use a
    lifecycle hook, the Auto Scaling group either pauses the instance after it
    is launched (before it is put into service) or pauses the instance as it
    is terminated (before it is fully terminated). For more information, see
    Examples of How to Use Lifecycle Hooks in the Auto Scaling Developer Guide.

    """
    def __init__(self, name):
        super(LifecycleHook, self).__init__('AWS::AutoScaling::LifecycleHook')
        self._name = name
        self._properties = {'AutoScalingGroupName': None,
                            'DefaultResult': None,
                            'HeartbeatTimeout': None,
                            'LifecycleTransition': None,
                            'NotificationMetadata': None,
                            'NotificationTargetARN': None,
                            'RoleARN': None}


class ScalingPolicy(base.Resource):
    """The AWS::AutoScaling::ScalingPolicy resource adds a scaling policy to an
    auto scaling group. A scaling policy specifies whether to scale the auto
    scaling group up or down, and by how much. For more information on scaling
    policies, see Scaling by Policy in the Auto Scaling Developer Guide.

    """
    def __init__(self, name):
        super(ScalingPolicy, self).__init__('AWS::AutoScaling::ScalingPolicy')
        self._name = name
        self._properties = {'AdjustmentType': None,
                            'AutoScalingGroupName': None,
                            'Cooldown': None,
                            'MinAdjustmentStep': None,
                            'ScalingAdjustment': None}


class ScheduledAction(base.Resource):
    """Creates a scheduled scaling action for an Auto Scaling group, changing
    the number of servers available for your application in response to
    predictable load changes.

    """
    def __init__(self, name):
        super(ScheduledAction,
              self).__init__('AWS::AutoScaling::ScheduledAction')
        self._name = name
        self._properties = {'AutoScalingGroupName': None,
                            'DesiredCapacity': None,
                            'EndTime': None,
                            'MaxSize': None,
                            'MinSize': None,
                            'Recurrence': None,
                            'StartTime': None}
