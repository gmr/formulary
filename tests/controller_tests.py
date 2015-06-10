"""

"""
import mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import uuid


from formulary import controller


class ControllerInitializationTests(unittest.TestCase):

    def _path_exists_side_effects(self, value=True):
        return [value for _i in range(0, len(controller.CONFIG_FILES) + 2)]

    def test_invalid_action(self):
        self.assertFalse(controller.Controller._validate_action('foo'))

    def test_valid_action(self):
        self.assertTrue(controller.Controller._validate_action('create'))

    def test_invalid_resource_type(self):
        self.assertFalse(controller.Controller._validate_resource_type('foo'))

    def test_valid_resource_type(self):
        self.assertTrue(controller.Controller._validate_resource_type('rds'))

    def test_invalid_config_dir(self):
        path = str(uuid.uuid4())
        self.assertFalse(controller.Controller._validate_config_path(path))

    @mock.patch('os.path.exists')
    def test_valid_config_dir(self, exists):
        exists.side_effect = self._path_exists_side_effects()
        path = str(uuid.uuid4())
        self.assertTrue(controller.Controller._validate_config_path(path))

    def test_invalid_environment(self):
        path = str(uuid.uuid4())
        env = str(uuid.uuid4())
        self.assertFalse(controller.Controller._validate_environment(path,
                                                                     env))

    @mock.patch('os.path.exists')
    def test_valid_config_dir(self, exists):
        exists.side_effect = self._path_exists_side_effects()
        path = str(uuid.uuid4())
        env = str(uuid.uuid4())
        self.assertTrue(controller.Controller._validate_environment(path,
                                                                    env))

    def test_invalid_reource(self):
        path = str(uuid.uuid4())
        resource_type = str(uuid.uuid4())
        resource = str(uuid.uuid4())
        self.assertFalse(controller.Controller._validate_resource(path,
                                                                  resource_type,
                                                                  resource))

    @mock.patch('os.path.exists')
    def test_valid_config_dir(self, exists):
        exists.side_effect = self._path_exists_side_effects()
        path = str(uuid.uuid4())
        resource_type = str(uuid.uuid4())
        resource = str(uuid.uuid4())
        self.assertTrue(controller.Controller._validate_resource(path,
                                                                 resource_type,
                                                                 resource))

    def test_validate_arguments_invalid_action(self):
        self.assertRaises(ValueError,
                          controller.Controller._validate_arguments,
                          None, 'foo', None, None, None)

    def test_validate_arguments_invalid_config_dir(self):
        self.assertRaises(ValueError,
                          controller.Controller._validate_arguments,
                          str(uuid.uuid4()), 'create', None, None, None)

    def test_validate_arguments_invalid_resource_type(self):
        self.assertRaises(ValueError,
                          controller.Controller._validate_arguments,
                          None, 'create', None, 'foo', None)

    @mock.patch('os.path.exists')
    def test_validate_arguments_invalid_environment(self, exists):
        side_effects = self._path_exists_side_effects()
        side_effects[-1] = False
        exists.side_effect = side_effects
        self.assertRaises(ValueError,
                          controller.Controller._validate_arguments,
                          str(uuid.uuid4()), 'create', str(uuid.uuid4()),
                          'rds', None)

    @mock.patch('os.path.exists')
    def test_validate_arguments_invalid_resource(self, exists):
        side_effects = self._path_exists_side_effects()
        side_effects += [False]
        exists.side_effect = side_effects
        self.assertRaises(ValueError,
                          controller.Controller._validate_arguments,
                          str(uuid.uuid4()), 'create', str(uuid.uuid4()),
                          'rds', 'foo')

    @mock.patch('os.path.exists')
    def test_validate_arguments_invalid_resource(self, exists):
        side_effects = self._path_exists_side_effects()
        side_effects += [True]
        exists.side_effect = side_effects
        result = controller.Controller._validate_arguments(str(uuid.uuid4()),
                                                           'create',
                                                           str(uuid.uuid4()),
                                                           'rds', 'foo')
        self.assertIsNone(result)
