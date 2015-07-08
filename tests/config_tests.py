"""
Controller Tests

"""
import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import uuid

from formulary import config


class ConfigTests(unittest.TestCase):

    def _path_exists_side_effects(self, value=True):
        return [value for _i in range(0, len(config.CONFIG_FILES) + 2)]

    def test_invalid_environment(self):
        path = str(uuid.uuid4())
        env = str(uuid.uuid4())
        self.assertFalse(config.ResourceConfig.validate_environment(path, env))

    @mock.patch('os.path.exists')
    def test_valid_config_dir(self, exists):
        exists.side_effect = self._path_exists_side_effects()
        path = str(uuid.uuid4())
        env = str(uuid.uuid4())
        self.assertTrue(config.ResourceConfig.validate_environment(path, env))

    def test_invalid_reource(self):
        path = str(uuid.uuid4())
        resource_type = 'service'
        resource = str(uuid.uuid4())
        self.assertFalse(config.ResourceConfig.validate_resource(path,
                                                                 resource_type,
                                                                 resource))

    @mock.patch('os.path.exists')
    def test_valid_config_dir(self, exists):
        exists.side_effect = self._path_exists_side_effects()
        path = str(uuid.uuid4())
        resource_type = 'service'
        resource = str(uuid.uuid4())
        self.assertTrue(config.ResourceConfig.validate_resource(path,
                                                                resource_type,
                                                                resource))
