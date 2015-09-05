"""
Cloud Formation Auto-Scaling Resources

AWS::AutoScaling::AutoScalingGroup
AWS::AutoScaling::LaunchConfiguration
AWS::AutoScaling::LifecycleHook
AWS::AutoScaling::ScalingPolicy
AWS::AutoScaling::ScheduledAction

"""
from formulary.resources import base


class AutoScalingBlockDeviceMapping(base.Property):
    """The AutoScaling Block Device Mapping type is an embedded property of the
    AWS::AutoScaling::LaunchConfiguration type.

    """
    def __init__(self, device_name=None, ebs=None, no_device=None,
                 virtual_name=None):
        super(AutoScalingBlockDeviceMapping, self).__init__()
        self._values = {'DeviceName': device_name,
                        'Ebs': ebs,
                        'NoDevice': no_device,
                        'VirtualName': virtual_name}


class AutoScalingBlockDevice(base.Property):
    """The AutoScaling EBS Block Device type is an embedded property of the
    AutoScaling Block Device Mapping type.

    """
    def __init__(self, delete_on_termination=None, iops=None, snapshot_id=None,
                 volume_size=None, volume_type=None):
        super(AutoScalingBlockDevice, self).__init__()
        self._values = {'DeleteOnTermination': delete_on_termination,
                        'iops': iops,
                        'SnapshotId': snapshot_id,
                        'VolumeSize': volume_size,
                        'VolumegType': volume_type}


class AutoScalingGroup(base.Resource):
    """The AWS::AutoScaling::AutoScalingGroup type creates an Auto Scaling
    group.

    """
    def __init__(self, name, availability_zones, cooldown,
                 health_check_grace_period, health_check_type, instance_id,
                 launch_configuration, load_balancer_names=None, min_size=1,
                 max_size=1, metrics=None, notifications=None,
                 placement_group=None, tags=None, termination_policies=None,
                 vpc_zone=None, dependency=None):
        super(AutoScalingGroup,
              self).__init__('AWS::AutoScaling::AutoScalingGroup')
        self._name = name
        self._properties = {'AvailabilityZones': availability_zones,
                            'Cooldown': cooldown,
                            'DesiredCapacity': min_size,
                            'HealthCheckGracePeriod': health_check_grace_period,
                            'HealthCheckType': health_check_type,
                            'InstanceId': instance_id,
                            'LaunchConfigurationName': launch_configuration,
                            'LoadBalancerNames': load_balancer_names,
                            'MaxSize': max_size,
                            'MetricsCollection': metrics,
                            'MinSize': min_size,
                            'NotificationConfigurations': notifications,
                            'PlacementGroup': placement_group,
                            'Tags': tags,
                            'TerminationPolicies': termination_policies,
                            'VPCZoneIdentifier': vpc_zone}
        if dependency:
            self.set_dependency({"Ref": dependency})


class AutoScalingMetricsCollection(base.Property):
    """The MetricsCollection is a property of the
    AWS::AutoScaling::AutoScalingGroup resource that describes the group
    metrics that an Auto Scaling group sends to CloudWatch. These metrics
    describe the group rather than any of its instances. For more information,
    see EnableMetricsCollection in the Auto Scaling API Reference.

    """
    def __init__(self, granularity=None, metrics=None):
        super(AutoScalingMetricsCollection, self).__init__()
        self._values = {'Granularity': granularity or [],
                        'Metrics': metrics or []}


class AutoScalingNotificationConfigurations(base.Property):
    """The NotificationConfigurations property is an embedded property of the
    AWS::AutoScaling::AutoScalingGroup resource that specifies the events for
    which the Auto Scaling group sends notifications.

    Valid NotificationTypes:

     - autoscaling:EC2_INSTANCE_LAUNCH
     - autoscaling:EC2_INSTANCE_LAUNCH_ERROR
     - autoscaling:EC2_INSTANCE_TERMINATE
     - autoscaling:EC2_INSTANCE_TERMINATE_ERROR
     - autoscaling:TEST_NOTIFICATION

    """
    def __init__(self, notification_types=None, topic_arn=None):
        super(AutoScalingNotificationConfigurations, self).__init__()
        self._values = {'NotificationTypes': notification_types,
                        'TopicARN': topic_arn}


class LaunchConfiguration(base.Resource):
    """The AWS::AutoScaling::LaunchConfiguration type creates an Auto Scaling
    launch configuration that can be used by an Auto Scaling group to configure
    Amazon EC2 instances in the Auto Scaling group.

    """
    def __init__(self, name, ami, block_devices, instance_type, key_pair,
                 security_group, user_data, ebs=True, monitoring=True,
                 public_ip=False, spot_price=None):
        super(LaunchConfiguration,
              self).__init__('AWS::AutoScaling::LaunchConfiguration')
        self._name = name
        self._properties = {'AssociatePublicIpAddress': public_ip,
                            'BlockDeviceMappings': block_devices,
                            'ClassicLinkVPCId': None,
                            'ClassicLinkVPCSecurityGroups': [],
                            'EbsOptimized': ebs,
                            'IamInstanceProfile': None,
                            'ImageId': ami,
                            'InstanceId': None,
                            'InstanceMonitoring': monitoring,
                            'InstanceType': instance_type,
                            'KernelId': None,
                            'KeyName': key_pair,
                            'PlacementTenancy': None,
                            'RamDiskId': None,
                            'SecurityGroups': [security_group],
                            'SpotPrice': spot_price,
                            'UserData': user_data}


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
    def __init__(self, name, adjustment_type, group_name, cooldown,
                 min_step, adjustment):
        super(ScalingPolicy, self).__init__('AWS::AutoScaling::ScalingPolicy')
        self._name = name
        self._properties = {'AdjustmentType': adjustment_type,
                            'AutoScalingGroupName': group_name,
                            'Cooldown': cooldown,
                            'MinAdjustmentStep': min_step,
                            'ScalingAdjustment': adjustment}


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
