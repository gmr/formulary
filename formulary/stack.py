"""
Cloud FormationStack

"""
import json
import logging

from boto import cloudformation
from boto import vpc

from formulary import records
from formulary import utils

LOGGER = logging.getLogger(__name__)

class _API(object):

    def __init__(self, region, profile):
        kwargs = {'profile_name': profile} if profile else {}
        LOGGER.debug('Connecting with profile: %r', kwargs)
        self._cf = cloudformation.connect_to_region(region, **kwargs)
        self._vpc = vpc.connect_to_region(region, **kwargs)

    def close(self):
        self._cf.close()
        self._vpc.close()

    @property
    def cf(self):
        """Return the connection handle to the Cloud Formation API

        :rtype: boto.cloudformation.connection.CloudFormationConnection

        """
        return self._cf

    @property
    def vpc(self):
        """Return the connection handle to the VPC API

        :rtype: boto.vpc.VPCConnection

        """
        return self._vpc

class Stack(object):

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
        :type value: boto.cloudformation.stack.StackResource
        :rtype: formulary.records.DHCPOptions

        """
        record = self._describe_dhcp_options(value.physical_resource_id)
        options = record.options
        domain = options['domain-name'][0] if options['domain-name'] else None
        return records.DHCPOptions(value.physical_resource_id,
                                   value.logical_resource_id,
                                   value.timestamp.isoformat(),
                                   value.resource_status,
                                   domain,
                                   options['domain-name-servers'][0],
                                   options['ntp-servers'][0],
                                   record.tags)

    @staticmethod
    def _create_dhcp_options_assoc_tuple(value):
        """Create the DHCPOptionsAssociation tuple from the retrieved stack
        resource information

        :param value: The DHCPOptionsAssociation stack entry
        :type value: boto.cloudformation.stack.StackResource
        :rtype: formulary.records.DHCPOptionsAssociation

        """
        return records.DHCPOptionsAssociation(value.physical_resource_id,
                                              value.logical_resource_id,
                                              value.timestamp.isoformat(),
                                              value.resource_status)

    @staticmethod
    def _create_gateway_association_tuple(value):
        """Create the GatewayAssociation tuple from the retrieved stack
        resource information

        :param value: The gateway association stack entry
        :type value: boto.cloudformation.stack.StackResource
        :rtype: formulary.records.GatewayAssociation

        """
        return records.GatewayAssociation(value.physical_resource_id,
                                          value.logical_resource_id,
                                          value.timestamp.isoformat(),
                                          value.resource_status)

    @staticmethod
    def _create_internet_gateway_tuple(value):
        """Create the InternetGateway tuple from the retrieved stack resource
        information

        :param value: The internet gateway stack entry
        :type value: boto.cloudformation.stack.StackResource
        :rtype: formulary.records.InternetGateway

        """
        return records.InternetGateway(value.physical_resource_id,
                                       value.logical_resource_id,
                                       value.timestamp.isoformat(),
                                       value.resource_status)

    def _create_network_acl_tuple(self, value):
        """Create the NetworkACL tuple from the retrieved stack resource
        information

        :param value: The NetworkACL stack entry
        :type value: boto.cloudformation.stack.StackResource
        :rtype: formulary.records.NetworkACL

        """
        acl_data = self._describe_network_acl(value.physical_resource_id)
        entries = []
        for entry in acl_data.network_acl_entries:
            from_port = int(entry.port_range.from_port) \
                if entry.port_range.from_port else None
            to_port = int(entry.port_range.to_port) \
                if entry.port_range.to_port else None
            acl_entry = records.NetworkACLEntry(None, None, None,
                                                int(entry.rule_number),
                                                entry.cidr_block,
                                                bool(entry.egress),
                                                entry.rule_action,
                                                int(entry.protocol),
                                                from_port, to_port)
            entries.append(acl_entry)
        return records.NetworkACL(value.physical_resource_id,
                                  value.logical_resource_id,
                                  value.timestamp.isoformat(),
                                  value.resource_status,
                                  entries,
                                  acl_data.tags)

    @staticmethod
    def _create_network_acl_tuple_entry(value):
        """Create the NetworkACLEntry tuple from the retrieved stack resource
        information

        :param value: The Network ACL entry stack entry
        :type value: boto.cloudformation.stack.StackResource
        :rtype: formulary.records.NetworkACL

        """
        return records.NetworkACLEntry(value.logical_resource_id,
                                       value.timestamp.isoformat(),
                                       value.resource_status,
                                       None, None, None, None, None, None, None)

    @staticmethod
    def _create_route_tuple(value):
        """Create the Route tuple from the retrieved stack resource
        information

        :param value: The route stack entry
        :type value: boto.cloudformation.stack.StackResource
        :rtype: formulary.records.Route

        """
        return records.Route(value.physical_resource_id,
                             value.logical_resource_id,
                             value.timestamp.isoformat(),
                             value.resource_status)

    def _create_route_table_tuple(self, value):
        """Create the RouteTable tuple from the retrieved stack resource
        information

        :param value: The route table stack entry
        :type value: boto.cloudformation.stack.StackResource
        :rtype: formulary.records.RouteTable

        """
        data = self._describe_route_table(value.physical_resource_id)
        associations = [d.subnet_id for d in data.associations]
        return records.RouteTable(value.physical_resource_id,
                                  value.logical_resource_id,
                                  value.timestamp.isoformat(),
                                  value.resource_status,
                                  associations,
                                  data.tags)

    def _create_subnet_tuple(self, value):
        """Create the Subnet tuple from the retrieved stack resource
        information

        :param value: The subnet stack entry
        :type value: boto.cloudformation.stack.StackResource
        :rtype: formulary.records.Subnet

        """
        data = self._describe_subnet(value.physical_resource_id)
        return records.Subnet(value.physical_resource_id,
                              value.logical_resource_id,
                              value.timestamp.isoformat(),
                              value.resource_status,
                              data.availability_zone,
                              data.cidr_block,
                              data.available_ip_address_count)

    @staticmethod
    def _create_subnet_route_table_association(value):
        """Create the SubnetRouteTableAssociation tuple from the retrieved
        stack resource information

        :param value: The route stack entry
        :type value: boto.cloudformation.stack.StackResource
        :rtype: formulary.records.SubnetRouteTableAssociation

        """
        return records.SubnetRouteTableAssociation(value.physical_resource_id,
                                                   value.logical_resource_id,
                                                   value.timestamp.isoformat(),
                                                   value.resource_status)

    def _create_vpc_tuple(self, value):
        """Create the VPC tuple from the retrieved stack resource information

        :param value: The VPC stack entry
        :type value: boto.cloudformation.stack.StackResource
        :return: formulary.records.VPC

        """
        vpc_data = self._describe_vpc(value.physical_resource_id)
        return records.VPC(value.physical_resource_id,
                           value.logical_resource_id,
                           value.timestamp.isoformat(),
                           vpc_data.state if vpc_data else None,
                           value.description,
                           vpc_data.cidr_block if vpc_data else None,
                           vpc_data.is_default if vpc_data else None,
                           vpc_data.instance_tenancy if vpc_data else None,
                           vpc_data.dhcp_options_id if vpc_data else None,
                           vpc_data.tags if vpc_data else None)

    def _describe_dhcp_options(self, dhcp_id):
        """Get the data from AWS about the specified DHCP options

        :param str dhcp_id: The ID to lookup
        :rtype: boto.vpc.dhcpoptions.DhcpOptions

        """
        LOGGER.debug('Fetching data for %s', dhcp_id)
        results = self._api.vpc.get_all_dhcp_options(dhcp_id)
        return results[0] if results else None

    def _describe_internet_gateway(self, gateway_id):
        """Get the data from AWS about the specified internet gateway

        :param str gateway_id: The ID to lookup
        :rtype: boto.vpc.internetgateway.InternetGateway

        """
        LOGGER.debug('Fetching data for %s', gateway_id)
        results = self._api.vpc.get_all_internet_gateways(gateway_id)
        return results[0] if results else None

    def _describe_route_table(self, route_table_id):
        """Get the data from AWS about the specified route table

        :param str route_table_id: The ID to lookup
        :rtype: boto.vpc.routetable.RouteTable

        """
        LOGGER.debug('Fetching data for %s', route_table_id)
        results = self._api.vpc.get_all_route_tables(route_table_id)
        return results[0] if results else None

    def _describe_stack(self):
        """Fetch the core stack configuration data

        :rtype: boto.cloudformation.stack.Stack

        """
        LOGGER.debug('Fetching data for %s', self._name)
        stacks = self._api.cf.describe_stacks(self._name)
        if not stacks:
            raise ValueError('Environment "{0}" not found'.format(self._name))
        return stacks[0]

    def _describe_stack_resources(self):
        """Fetch the resources for the stack

        :rtype: list

        """
        function_map = self._build_api_create_function_map()

        LOGGER.debug('Fetching stack resources')
        resources = []
        result = self._api.cf.describe_stack_resources(self._name)
        for row in result:
            try:
                resources.append(function_map[row.resource_type](row))
            except KeyError:
                LOGGER.debug('Row data: %r', row.__dict__)
                raise NotImplementedError(row.resource_type)
        return resources

    def _describe_network_acl(self, acl_id):
        """Get the data from AWS about the network ACL

        :param str acl_id: The ID to lookup
        :rtype: boto.vpc.networkacl.NetworkAcl

        """
        LOGGER.debug('Fetching data for %s', acl_id)
        results = self._api.vpc.get_all_network_acls(acl_id)
        return results[0] if results else None

    def _describe_subnet(self, subnet_id):
        """Fetch the subnet configuration data

        :rtype: boto.vpc.subnet.Subnet

        """
        LOGGER.debug('Fetching data for %s', subnet_id)
        results = self._api.vpc.get_all_subnets(subnet_id)
        return results[0] if results else None

    def _describe_vpc(self, vpc_id):
        """Get the data from AWS about the VPC

        :param str vpc_id: The ID to lookup
        :rtype: boto.vpc.vpc.VPC

        """
        LOGGER.debug('Fetching data for %s', vpc_id)
        results = self._api.vpc.get_all_vpcs(vpc_id)
        return results[0] if results else None

    def _process_api_data(self):
        """Build the stack resources from a combination of remote API calls
        to various AWS endpoints.

        """
        LOGGER.debug('Processing API data')
        self._api = _API(self._region, self._profile)
        stack = self._describe_stack()
        self._description = stack.description
        self._id = stack.stack_id
        self._status = stack.stack_status
        self._resources = self._describe_stack_resources()
        self._api.close()

    def _process_template(self, template):
        values = json.loads(template.as_json())
        self._description = values['Description']
        # @TODO add resource tuples
