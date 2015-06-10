"""
Cloud Formation methods and interfaces

"""
import collections
import json
import logging

from boto import cloudformation
from boto import exception

LOGGER = logging.getLogger(__name__)

StackResource = collections.namedtuple('StackResource',
                                       ('id', 'type', 'name', 'status'))


def create_stack(region, template, profile):
    """Create a stack in the specified region with the given template.

    :param str region: The region name to create the stack in
    :param Template template: The template to use
    :param str profile: The credentials profile to use
    :raises: RequestException

    """
    kwargs = {'profile_name': profile} if profile else {}
    connection = cloudformation.connect_to_region(region, **kwargs)
    template_body = template.as_json()
    if not connection.validate_template(template_body):
        raise RequestException('The specified template did not validate')
    try:
        connection.create_stack(template.name, template_body)
    except exception.BotoServerError as error:
        raise RequestException(error)
    connection.close()


def estimate_stack_cost(region, template, profile):
    """Estimate the cost of the stack in EC2

    :param str region: The region name to create the stack in
    :param Template template: The template to use
    :param str profile: The credentials profile to use
    :raises: RequestException

    """
    kwargs = {'profile_name': profile} if profile else {}
    connection = cloudformation.connect_to_region(region, **kwargs)
    template_body = template.as_json()
    if not connection.validate_template(template_body):
        raise RequestException('The specified template did not validate')
    try:
        result = connection.estimate_template_cost(template_body)
    except exception.BotoServerError as error:
        raise RequestException(error)
    connection.close()
    return result


def update_stack(region, template, profile):
    """Update a stack in the specified region with the given template.

    :param str region: The region name to create the stack in
    :param Template template: The template to use
    :param str profile: The credentials profile to use
    :raises: RequestException

    """
    kwargs = {'profile_name': profile} if profile else {}
    connection = cloudformation.connect_to_region(region, **kwargs)
    template_body = template.as_json()
    if not connection.validate_template(template_body):
        raise RequestException('The specified template did not validate')
    try:
        connection.update_stack(template.name, template_body)
    except exception.BotoServerError as error:
        raise RequestException(error)
    connection.close()


class RequestException(Exception):
    def __init__(self, error):
        error = str(error)
        payload = json.loads(error[error.find('{'):])
        self._message = payload['Error']['Message']

    def __repr__(self):
        return '<{0} "{1}">'.format(self._message)

    def __str__(self):
        return self._message
