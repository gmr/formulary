"""
Build Cloud Formation EC2 stacks

"""
import logging

from formulary.resources import autoscaling
from formulary.builders import base
from formulary.builders import ec2

LOGGER = logging.getLogger(__name__)

DEFAULT_INSTANCE_TYPE = ec2.DEFAULT_INSTANCE_TYPE
USER_DATA_RE = ec2.USER_DATA_RE
USER_DATA_JSON = ec2.USER_DATA_JSON



class AutoScalingGroup(base.Builder):

    def __init__(self, config, name, availability_zones, cooldown,
                 health_check_grace_period, health_check_type, instance_id,
                 launch_configuration, load_balancer_names=None, min_size=1,
                 max_size=1, metrics=None, notifications=None,
                 placement_group=None, tags=None, termination_policies=None,
                 vpc_zones=None, dependency=None):
        super(AutoScalingGroup, self).__init__(config, name)
        resource = autoscaling.AutoScalingGroup(self.full_name,
                                                availability_zones,
                                                cooldown,
                                                health_check_grace_period,
                                                health_check_type,
                                                instance_id,
                                                launch_configuration,
                                                load_balancer_names,
                                                min_size,
                                                max_size,
                                                metrics,
                                                notifications,
                                                placement_group,
                                                tags,
                                                termination_policies,
                                                vpc_zones,
                                                dependency)
        ref_id = self._add_resource(self.name, resource)
        self._add_output('ScalingPolicyId',
                         'The logical ID for {0}'.format(self.full_name),
                         {'Ref': ref_id})


class LaunchConfiguration(ec2.InstanceBuilder):

    def __init__(self, config, name, ami, block_devices, instance_type,
                 key_pair, public_ip, security_group, user_data,
                 ebs=True, metadata=None, monitoring=True, stack_name=None):
        """Create a new EC2 instance builder

        :param formulary.builders.config.Config: builder configuration
        :param str name:
        :param str ami:
        :param list block_devices:
        :param str instance_type:
        :param str private_ip:
        :param str security_group:
        :param formulary.resources.ec2.Subnet subnet:
        :param str user_data:
        :param bool ebs: Is EBS backed
        :param str stack_name: The name of the parent stack for the instance

        """
        super(LaunchConfiguration, self).__init__(config, name)

        # Build kwargs used for user-data template and ec2.Instance
        kwargs = {'name': self.full_name,
                  'ami': ami,
                  'block_devices': block_devices,
                  'environment': config.environment,
                  'instance_type': instance_type,
                  'key_pair': key_pair,
                  'monitoring': monitoring,
                  'public_ip': public_ip,
                  'ref_id': self.reference_id,
                  'region': config.region,
                  'service': config.service,
                  'security_group': security_group,
                  'spot_price': None,
                  'stack': stack_name,
                  'ebs': ebs}

        if metadata:
            kwargs.update(metadata)

        kwargs['user_data'] = self._render_user_data(user_data, kwargs)

        if metadata:
            for key in metadata:
                del kwargs[key]

        # Remove the kwargs that don't get passed to ec2.Instance
        for key in ['environment', 'ref_id', 'region', 'service', 'stack']:
            del kwargs[key]

        resource = autoscaling.LaunchConfiguration(**kwargs)
        ref_id = self._add_resource(self.name, resource)

        # Add private and public IP output
        self._add_output('LaunchConfig',
                         'The logical ID for {0}'.format(self.full_name),
                         {'Ref': ref_id})


class ScalingPolicy(base.Builder):

    def __init__(self, config, name, adjustment_type, group_name, cooldown,
                 min_step, adjustment):
        super(ScalingPolicy, self).__init__(config, name)
        resource = autoscaling.ScalingPolicy(self.full_name,
                                             adjustment_type,
                                             group_name,
                                             cooldown,
                                             min_step,
                                             adjustment)
        ref_id = self._add_resource(self.name, resource)
        self._add_output('ScalingPolicyId',
                         'The logical ID for {0}'.format(self.full_name),
                         {'Ref': ref_id})
