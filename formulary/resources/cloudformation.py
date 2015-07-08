"""
Cloud Formation Resources

"""
from formulary.resources import base


class Stack(base.Resource):
    """The AWS::CloudFormation::Stack type nests a stack as a resource in a
    top-level template.

    You can add output values from a nested stack within the containing
    template. You use the GetAtt function with the nested stack's logical name
    and the name of the output value in the nested stack in the format
    Outputs.NestedStackOutputName.

    When you apply template changes to update a top-level stack, AWS
    CloudFormation updates the top-level stack and initiates an update to
    its nested stacks. AWS CloudFormation updates the resources of modified
    nested stacks, but does not update the resources of unmodified nested
    stacks.

    """
    tags = False

    def __init__(self, template_url, parameters=None, notifications=None,
                 timeout=None):
        super(Stack, self).__init__('AWS::CloudFormation::Stack')
        self._properties = {'NotificationARNs': notifications,
                            'Parameters': parameters,
                            'TemplateURL': template_url,
                            'TimeoutInMinutes': timeout}


class WaitCondition(base.CPResource):
    """You can use a wait condition for situations like the following:

    To coordinate stack resource creation with configuration actions that are
    external to the stack creation

    To track the status of a configuration process

    For these situations, we recommend that you associate a CreationPolicy
    attribute with the wait condition so that you don't have to use a wait
    condition handle. For more information and an example, see Creating Wait
    Conditions in a Template. If you use a CreationPolicy with a wait
    condition, do not specify any of the wait condition's properties.

    """
    tags = False

    def __init__(self, count=None, handle=None, timeout=None):
        super(WaitCondition,
              self).__init__('AWS::CloudFormation::WaitCondition')
        self._properties = {'Count': count,
                            'Handle': handle,
                            'Timeout': timeout}


class WaitConditionHandle(base.Resource):
    """The AWS::CloudFormation::WaitConditionHandle type has no properties.
    When you reference the WaitConditionHandle resource by using the Ref
    function, AWS CloudFormation returns a presigned URL. You pass this URL to
    applications or scripts that are running on your Amazon EC2 instances to
    send signals to that URL. An associated AWS::CloudFormation::WaitCondition
    resource checks the URL for the required number of success signals or for
    a failure signal.

    """
    tags = False

    def __init__(self):
        super(WaitConditionHandle,
              self).__init__('AWS::CloudFormation::WaitConditionHandle')
        self._properties = {}
