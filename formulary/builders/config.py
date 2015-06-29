"""
Builder Configuration

"""
class Config(object):
    """Configuration class for Builder objects"""
    def __init__(self, settings, mappings, region, s3_bucket, s3_prefix,
                 environment=None, service=None):
        """Create a new instance of a Config class

        :param dict settings: Settings from configuration files
        :param dict mappings: Mapping configuration
        :param str region: AWS region name
        :param str s3_bucket: The formulary S3 work bucket
        :param str s3_prefix: s3 work prefix
        :param str|None environment: The optional formulary environment name
        :param str|None service:  Formulary service name if set

        """
        self.settings = self._flatten_settings(settings, environment)
        self.environment = environment
        self.mappings = mappings
        self.region = region
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix
        self.service = service

    def _flatten_settings(self, settings, environment):
        out = {}
        for key, value in settings.items():
            if isinstance(value, dict):
                for value_key in settings[key].keys():
                    if value_key == environment:
                        out[key] = settings[key][value_key]
                        break
                    elif value_key == 'default':
                        out[key] = settings[key]['default']
                        break
                    else:
                        out[key] = self._flatten_settings(value, environment)
            else:
                out[key] = value
        return out
