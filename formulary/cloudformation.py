"""
Cloud Formation methods and interfaces

"""
import collections
import json
import logging
import uuid

from boto3 import session
from botocore import exceptions

from formulary import records
from formulary import s3
from formulary import utils

LOGGER = logging.getLogger(__name__)
MAX_TEMPLATE_SIZE = 51200

StackResource = collections.namedtuple('StackResource',
                                       ('id', 'type', 'name', 'status'))


class CloudFormation(object):
    """Class for interfacing with Cloud Formation and related APIs"""

    def __init__(self, profile, region, s3bucket_name, s3bucket_path):
        """Estimate the cost of the stack in EC2

        :param str region: The region name to create the stack in
        :param str bucket: The bucket to use for large templates
        :param str profile: The credentials profile to use

        """
        self._s3 = s3.S3(s3bucket_name, s3bucket_path, profile)

        self._session = session.Session(profile_name=profile,
                                        region_name=region)
        self._client = self._session.client('cloudformation')

    def create_stack(self, template, environment, service=None):
        """Create a stack in the specified region with the given template,
        returning the stack id.

        :param Template template: The template to use
        :param str environment: The environment to set in a stack tag
        :param str|None service: The service name to set in a stack tag
        :rtype: str

        """
        template_id = str(uuid.uuid4())
        url = self._s3.upload(template_id, template.as_json())
        tags = [{'Key': 'Environment', 'Value': environment}]
        if service:
            tags.append({'Key': 'Service', 'Value': service})
        try:
            result = self._client.create_stack(StackName=template.name,
                                               Tags=tags,
                                               TemplateURL=url)
        except exceptions.ClientError as error:
            self._s3.delete(template_id)
            raise RequestException(error)

        LOGGER.debug('Created stack ID: %r', result['StackId'])

        # Upload stack details for removing completed stacks
        stack_details = {'id': result['StackId'],
                         'name': template.name,
                         'environment': environment}
        self._s3.upload('stack.json', json.dumps(stack_details))

        return result['StackId']

    def update_stack(self, template):
        """Update a stack in the specified region with the given template.

        :param Template template: The template to use
        :raises: RequestException

        """
        template_id = str(uuid.uuid4())
        url = self._s3.upload(template_id, template.as_json())
        try:
            result = self._client.update_stack(StackName=template.name,
                                               TemplateURL=url)
        except exceptions.ClientError as error:
            self._s3.delete(template_id)
            raise RequestException(error)
        LOGGER.debug('Updated stack ID: %r', result['StackId'])


class _API(object):

    def __init__(self, region, profile):
        kwargs = {'profile_name': profile} if profile else {}
        LOGGER.debug('Connecting with profile: %r', kwargs)
        self._session = session.Session(profile_name=profile,
                                        region_name=region)
        self._cf = self._session.client('cloudformation')
        self._ec2 = self._session.resource('ec2')

    @property
    def cf(self):
        """Return the connection handle to the Cloud Formation API

        :rtype: botocore.client.CloudFormation

        """
        return self._cf

    @property
    def ec2(self):
        """Return the connection handle to the EC2 API

        :rtype: botocore.client.EC2

        """
        return self._ec2


class EnvironmentStack(object):

    def __init__(self, name, config, template=None, profile=None):
        self._config = config
        self._name = name
        self._profile = profile
        self._region = config.get('region')

        self._api = None
        self._description = None
        self._id = None
        self._resources = {}
        self._status = None
        if template:
            self._process_template(template)
        else:
            self._process_api_data()

    @property
    def cidr_block(self):
        """Return the CIDR block for the Stack's VPC

        :rtype: str

        """
        return self.vpc.cidr_block

    @property
    def environment(self):
        """Return the environment from the Stack's tags

        :rtype: str

        """
        return self.vpc.tags.get('Environment', self._name)

    @property
    def mappings(self):
        """Return mappings based upon values in the stack used for service
        configuration and user-data templates.

        :rtype: dict

        """
        vpc_data = dict()
        for key, value in self.vpc._asdict().items():
            if key == 'tags':
                continue
            cckey = utils.camel_case(key)
            if key == 'cidr_block':
                cckey = 'CIDR'
            if value is not None:
                vpc_data[cckey] = value
        return {
            'Network': {
                'Name': {'Value': self._name},
                'VPC': vpc_data,
                'AWS': {'Region': self._region}
            }
        }

    @property
    def name(self):
        """Return the stack name

        :rtype: str

        """
        return self._name

    @property
    def resources(self):
        """Return the resources associated with this stack

        :rtype: list

        """
        return self._resources

    @property
    def subnets(self):
        """Return a list of subnets associated with the stack

        :rtype: list of formulary.records.Subnet

        """
        return [r for r in self._resources if isinstance(r, records.Subnet)]

    @property
    def vpc(self):
        """Return the VPC if it is in the resources.

        :rtype: formulary.records.VPC

        """
        for resource in self._resources:
            if isinstance(resource, records.VPC):
                return resource

    def _build_api_create_function_map(self):
        return {
            'AWS::EC2::DHCPOptions': self._create_dhcp_options_tuple,
            'AWS::EC2::VPCDHCPOptionsAssociation':
                self._create_dhcp_options_assoc_tuple,
            'AWS::EC2::InternetGateway': self._create_internet_gateway_tuple,
            'AWS::EC2::NetworkAcl': self._create_network_acl_tuple,
            'AWS::EC2::NetworkAclEntry': self._create_network_acl_tuple_entry,
            'AWS::EC2::Route': self._create_route_tuple,
            'AWS::EC2::RouteTable': self._create_route_table_tuple,
            'AWS::EC2::Subnet': self._create_subnet_tuple,
            'AWS::EC2::SubnetRouteTableAssociation':
                self._create_subnet_route_table_association,
            'AWS::EC2::VPC': self._create_vpc_tuple,
            'AWS::EC2::VPCGatewayAttachment':
                self._create_gateway_association_tuple
        }

    def _create_dhcp_options_tuple(self, value):
        """Create the DHCPOptions tuple from the retrieved stack resource
        information

        :param value: The DHCPOptions stack entry
        :type value: dict
        :rtype: formulary.records.DHCPOptions

        """
        record = self._describe_dhcp_options(value['PhysicalResourceId'])
        cfg = dict()
        for cfg_value in record.dhcp_configurations:
            cfg[cfg_value['Key']] = cfg_value['Values']
        return records.DHCPOptions(value['PhysicalResourceId'],
                                   value['LogicalResourceId'],
                                   value['Timestamp'].isoformat(),
                                   value['ResourceStatus'],
                                   cfg['domain-name'][0],
                                   cfg['domain-name-servers'][0],
                                   cfg['ntp-servers'][0],
                                   record.tags)

    @staticmethod
    def _create_dhcp_options_assoc_tuple(value):
        """Create the DHCPOptionsAssociation tuple from the retrieved stack
        resource information

        :param value: The DHCPOptionsAssociation stack entry
        :type value: dict
        :rtype: formulary.records.DHCPOptionsAssociation

        """
        return records.DHCPOptionsAssociation(value['PhysicalResourceId'],
                                              value['LogicalResourceId'],
                                              value['Timestamp'].isoformat(),
                                              value['ResourceStatus'])

    @staticmethod
    def _create_gateway_association_tuple(value):
        """Create the GatewayAssociation tuple from the retrieved stack
        resource information

        :param value: The gateway association stack entry
        :type value: dict
        :rtype: formulary.records.GatewayAssociation

        """
        return records.GatewayAssociation(value['PhysicalResourceId'],
                                          value['LogicalResourceId'],
                                          value['Timestamp'].isoformat(),
                                          value['ResourceStatus'])

    @staticmethod
    def _create_internet_gateway_tuple(value):
        """Create the InternetGateway tuple from the retrieved stack resource
        information

        :param value: The internet gateway stack entry
        :type value: dict
        :rtype: formulary.records.InternetGateway

        """
        return records.InternetGateway(value['PhysicalResourceId'],
                                       value['LogicalResourceId'],
                                       value['Timestamp'].isoformat(),
                                       value['ResourceStatus'])

    def _create_network_acl_tuple(self, value):
        """Create the NetworkACL tuple from the retrieved stack resource
        information

        :param value: The NetworkACL stack entry
        :type value: dict
        :rtype: formulary.records.NetworkACL

        """
        acl_data = self._describe_network_acl(value['PhysicalResourceId'])
        entries = []
        for entry in acl_data.entries:
            from_port, to_port = None, None
            if entry.get('PortRange'):
                from_port = entry['PortRange'].Get('From')
                to_port = entry['PortRange'].Get('To')
            acl_entry = records.NetworkACLEntry(None, None, None,
                                                int(entry['RuleNumber']),
                                                entry['CidrBlock'],
                                                bool(entry['Egress']),
                                                entry['RuleAction'],
                                                int(entry['Protocol']),
                                                from_port, to_port)
            entries.append(acl_entry)
        return records.NetworkACL(value['PhysicalResourceId'],
                                  value['LogicalResourceId'],
                                  value['Timestamp'].isoformat(),
                                  value['ResourceStatus'],
                                  entries,
                                  acl_data.tags)

    @staticmethod
    def _create_network_acl_tuple_entry(value):
        """Create the NetworkACLEntry tuple from the retrieved stack resource
        information

        :param value: The Network ACL entry stack entry
        :type value: dict
        :rtype: formulary.records.NetworkACL

        """
        return records.NetworkACLEntry(value['PhysicalResourceId'],
                                       value['Timestamp'].isoformat(),
                                       value['ResourceStatus'],
                                       None, None, None, None, None, None, None)

    @staticmethod
    def _create_route_tuple(value):
        """Create the Route tuple from the retrieved stack resource
        information

        :param value: The route stack entry
        :type value: dict
        :rtype: formulary.records.Route

        """
        return records.Route(value['PhysicalResourceId'],
                             value['LogicalResourceId'],
                             value['Timestamp'].isoformat(),
                             value['ResourceStatus'])

    def _create_route_table_tuple(self, value):
        """Create the RouteTable tuple from the retrieved stack resource
        information

        :param value: The route table stack entry
        :type value: dict
        :rtype: formulary.records.RouteTable

        """
        data = self._describe_route_table(value['PhysicalResourceId'])
        associations = [d.subnet_id for d in data.associations.all()]
        return records.RouteTable(value['PhysicalResourceId'],
                                  value['LogicalResourceId'],
                                  value['Timestamp'].isoformat(),
                                  value['ResourceStatus'],
                                  associations,
                                  data.tags)

    def _create_subnet_tuple(self, value):
        """Create the Subnet tuple from the retrieved stack resource
        information

        :param value: The subnet stack entry
        :type value: dict
        :rtype: formulary.records.Subnet

        """
        data = self._describe_subnet(value['PhysicalResourceId'])
        return records.Subnet(value['PhysicalResourceId'],
                              value['LogicalResourceId'],
                              value['Timestamp'].isoformat(),
                              value['ResourceStatus'],
                              data.availability_zone,
                              data.cidr_block,
                              data.available_ip_address_count)

    @staticmethod
    def _create_subnet_route_table_association(value):
        """Create the SubnetRouteTableAssociation tuple from the retrieved
        stack resource information

        :param value: The route stack entry
        :type value: dict
        :rtype: formulary.records.SubnetRouteTableAssociation

        """
        return \
            records.SubnetRouteTableAssociation(value['PhysicalResourceId'],
                                                value['LogicalResourceId'],
                                                value['Timestamp'].isoformat(),
                                                value['ResourceStatus'])

    def _create_vpc_tuple(self, value):
        """Create the VPC tuple from the retrieved stack resource information

        :param value: The VPC stack entry
        :type value: boto3.resources.factory.ec2.Vpc
        :return: formulary.records.VPC

        """
        vpc = self._get_vpc_resource(value['PhysicalResourceId'])
        tags = dict()
        for tag in vpc.tags:
            tags[tag['Key']] = tag['Value']
        return records.VPC(value['PhysicalResourceId'],
                           value['LogicalResourceId'],
                           value['Timestamp'].isoformat(),
                           vpc.state if vpc else None,
                           None,
                           vpc.cidr_block if vpc else None,
                           vpc.is_default if vpc else None,
                           vpc.instance_tenancy if vpc else None,
                           vpc.dhcp_options_id if vpc else None,
                           tags)

    def _describe_dhcp_options(self, dhcp_id):
        """Get the data from AWS about the specified DHCP options

        :param str dhcp_id: The ID to lookup
        :rtype: boto3.resources.factory.ec2.DhcpOptions

        """
        LOGGER.debug('Fetching data for %s', dhcp_id)
        try:
            return self._api.ec2.DhcpOptions(dhcp_id)
        except exceptions.ClientError as error:
            raise RequestException(error)

    def _describe_internet_gateway(self, gateway_id):
        """Get the data from AWS about the specified internet gateway

        :param str gateway_id: The ID to lookup
        :rtype: boto3.resources.factory.ec2.InternetGateway

        """
        LOGGER.debug('Fetching data for %s', gateway_id)
        try:
            return self._api.ec2.InternetGateway(gateway_id)
        except exceptions.ClientError as error:
            raise RequestException(error)

    def _describe_route_table(self, route_table_id):
        """Get the data from AWS about the specified route table

        :param str route_table_id: The ID to lookup
        :rtype: boto3.resources.factory.ec2.RouteTable

        """
        LOGGER.debug('Fetching data for %s', route_table_id)
        try:
            return self._api.ec2.RouteTable(route_table_id)
        except exceptions.ClientError as error:
            raise RequestException(error)

    def _describe_stack(self):
        """Fetch the core stack configuration data

        :rtype: dict

        """
        LOGGER.debug('Fetching data for %s', self._name)
        try:
            response = self._api.cf.describe_stacks(StackName=self._name)
        except exceptions.ClientError as error:
            raise RequestException(error)
        return response['Stacks'][0]

    def _describe_stack_resources(self):
        """Fetch the resources for the stack

        :rtype: list

        """
        function_map = self._build_api_create_function_map()

        LOGGER.debug('Fetching stack resources')
        resources = []
        try:
            result = self._api.cf.describe_stack_resources(StackName=self._name)
        except exceptions.ClientError as error:
            raise RequestException(error)
        for row in result['StackResources']:
            try:
                resources.append(function_map[row['ResourceType']](row))
            except KeyError:
                LOGGER.debug('Row data: %r', row)
                raise NotImplementedError(row.resource_type)
        return resources

    def _describe_network_acl(self, acl_id):
        """Get the data from AWS about the network ACL

        :param str acl_id: The ID to lookup
        :rtype: boto3.resources.factory.ec2.NetworkAcl

        """
        LOGGER.debug('Fetching data for %s', acl_id)
        try:
            return self._api.ec2.NetworkAcl(acl_id)
        except exceptions.ClientError as error:
            raise RequestException(error)

    def _describe_subnet(self, subnet_id):
        """Fetch the subnet configuration data

        :rtype: boto3.resources.factory.ec2.Subnet

        """
        LOGGER.debug('Fetching data for %s', subnet_id)
        try:
            return self._api.ec2.Subnet(subnet_id)
        except exceptions.ClientError as error:
            raise RequestException(error)

    def _get_vpc_resource(self, vpc_id):
        """Get the data from AWS about the VPC

        :param str vpc_id: The ID to lookup
        :rtype: boto.vpc.vpc.VPC

        """
        LOGGER.debug('Fetching data for %s', vpc_id)
        try:
            return self._api.ec2.Vpc(vpc_id)
        except exceptions.ClientError as error:
            raise RequestException(error)

    def _process_api_data(self):
        """Build the stack resources from a combination of remote API calls
        to various AWS endpoints.

        """
        LOGGER.debug('Processing API data')
        self._api = _API(self._region, self._profile)
        stack = self._describe_stack()
        self._description = stack['Description']
        self._id = stack['StackId']
        self._status = stack['StackStatus']
        self._resources = self._describe_stack_resources()

    def _process_template(self, template):
        values = json.loads(template.as_json())
        self._description = values['Description']
        # @TODO add resource tuples



class RequestException(Exception):
    def __init__(self, error):
        self._message = error.response['Error']['Message']

    def __repr__(self):
        return '<{0} "{1}">'.format(self._message)

    def __str__(self):
        return self._message
