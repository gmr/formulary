"""
Cloud Formation (cf) object tests

"""
import json
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from formulary import cloudformation

VPC_EXPECTATION = {
    'Type': 'AWS::EC2::VPC',
    'Properties': {
        'EnableDnsSupport': True,
        'EnableDnsHostnames': True,
        'CidrBlock': '0.0.0.0/0',
        'Tags': [{'Key': 'foo',
                  'Value': 'bar'},
                 {'Key': 'Name',
                  'Value': 'vpc-test-name'}]
    }
}


class ResourceTests(unittest.TestCase):
    def test_as_json_with_no_tags(self):
        expectation = {
            'Type': 'AWS::EC2::DHCPOptions',
            'Properties': {
                'DomainName': 'foo',
                'DomainNameServers': ['8.8.4.4', '8.8.8.8'],
                'NtpServers': ['127.0.0.1']
            }
        }
        resource = cloudformation.Resource('AWS::EC2::DHCPOptions')
        resource.add_property('DomainName', 'foo')
        resource.add_property('DomainNameServers', ['8.8.4.4', '8.8.8.8'])
        resource.add_property('NtpServers', ['127.0.0.1'])
        self.assertDictEqual(resource.as_dict(), expectation)

    def test_as_json_with_an_attribute(self):
        expectation = {
            'Type': 'AWS::EC2::Route',
            'DependsOn': 'internet-gateway',
            'Properties': {
                'RouteTableId': {'ref': 'routing-table-id'},
                'DestinationCidrBlock': '0.0.0.0/0',
                'GatewayId': {'ref': 'gateway-id'}
            }
        }
        resource = cloudformation.Resource('AWS::EC2::Route')
        resource.add_property('RouteTableId', {'ref': 'routing-table-id'})
        resource.add_property('GatewayId', {'ref': 'gateway-id'})
        resource.add_property('DestinationCidrBlock', '0.0.0.0/0')
        resource.add_attribute('DependsOn', 'internet-gateway')
        self.assertDictEqual(resource.as_dict(), expectation)

    def test_as_json_with_tags(self):
        resource = cloudformation.Resource('AWS::EC2::VPC')
        resource.add_property('EnableDnsSupport', True)
        resource.add_property('EnableDnsHostnames', True)
        resource.add_property('CidrBlock', '0.0.0.0/0')
        resource.add_tag('foo', 'bar')
        self.assertDictEqual(resource.as_dict(), {
            'Type': 'AWS::EC2::VPC',
            'Properties': {
                'EnableDnsSupport': True,
                'EnableDnsHostnames': True,
                'CidrBlock': '0.0.0.0/0',
                'Tags': [{'Key': 'foo', 'Value': 'bar'}]
            }
        })

    def test_as_json_with_tags_and_name(self):
        resource = cloudformation.Resource('AWS::EC2::VPC')
        resource.set_name('vpc-test-name')
        resource.add_property('EnableDnsSupport', True)
        resource.add_property('EnableDnsHostnames', True)
        resource.add_property('CidrBlock', '0.0.0.0/0')
        resource.add_tag('foo', 'bar')
        self.assertDictEqual(resource.as_dict(), VPC_EXPECTATION)


class TemplateTests(unittest.TestCase):
    def test_mappings_json_values(self):
        expectation = {'foo': 'bar', 'baz': 'qux'}
        template = cloudformation.Template()
        template.update_mappings({'foo': 'bar', 'baz': 'qux'})
        result = json.loads(template.as_json())
        self.assertDictEqual(result['Mappings'], expectation)

    def test_resource_json_values(self):
        resource = cloudformation.Resource('AWS::EC2::VPC')
        resource.set_name('vpc-test-name')
        resource.add_property('EnableDnsSupport', True)
        resource.add_property('EnableDnsHostnames', True)
        resource.add_property('CidrBlock', '0.0.0.0/0')
        resource.add_tag('foo', 'bar')
        template = cloudformation.Template()
        template.add_resource('VPCTestName', resource)
        result = json.loads(template.as_json())
        self.assertDictEqual(result['Resources']['VPCTestName'],
                             VPC_EXPECTATION)
