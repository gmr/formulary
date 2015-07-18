"""
Build the resources for a RDS Instance

"""
from formulary.builders import base
from formulary.resources import route53


class Route53RecordSet(base.Builder):

    def __init__(self, config, name, settings, instances=None):
        super(Route53RecordSet, self).__init__(config, name)
        if instances:
            if 'srv' in settings:
                self._add_instance_srv(settings, instances)
            else:
                self._add_instance_rr(settings, instances)
        else:
            self._add_parameter('DNSName', {'Type': 'String'})
            self._add_parameter('HostedZoneId', {'Type': 'String'})
            self._add_alias_record(settings)

    def _add_alias_record(self, settings):
        alias = route53.Route53AliasTarget({'Ref': 'DNSName'},
                                           {'Ref': 'HostedZoneId'})
        self._add_resource('route53-{0}-a'.format(settings['hostname']),
                           route53.Route53RecordSet(settings['domain_name'],
                                                    settings['hostname'], None,
                                                    alias.as_dict(), 'A',
                                                    settings.get('ttl')))

    def _add_instance_rr(self, settings, instances):
        for instance in instances:
            self._add_parameter(instance, {'Type': 'String'})
        resources = [{'Ref': ref_id} for ref_id in instances]
        self._add_resource('route53-{0}-a'.format(settings['hostname']),
                           route53.Route53RecordSet(settings['domain_name'],
                                                    settings['hostname'],
                                                    resources, None, 'A',
                                                    settings.get('ttl')))

    def _add_instance_srv(self, settings, instances):
        for instance in instances:
            self._add_parameter(instance, {'Type': 'String'})
        resources = []
        srv = settings['srv']
        for ref_id in instances:
            resources.append({'Fn::Join': ['',
                                           [str(srv.get('priority', '0')), ' ',
                                            str(srv.get('weight', '0')), ' ',
                                            str(srv.get('port', '80')), ' ',
                                            {'Ref': ref_id}, '.']]})
        hostname = '_{0}._{1}'.format(settings['hostname'],
                                      srv.get('protocol', 'tcp'))
        self._add_resource('route53-{0}-srv'.format(settings['hostname']),
                           route53.Route53RecordSet(settings['domain_name'],
                                                    hostname,
                                                    resources, None, 'SRV',
                                                    settings.get('ttl')))
