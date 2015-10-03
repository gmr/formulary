"""
Upload to and remove stacks from S3

"""
import datetime
import logging

from boto3 import session
from botocore import exceptions

LOGGER = logging.getLogger(__name__)
TTL = 3600


class S3(object):
    """The S3 class is used to upload and delete stack files from AWS S3"""

    def __init__(self, bucket_name, root_path, profile):
        """Create a new instance of the S3 class passing in the bucket name
        and the root path for all files uploaded.

        :param str bucket_name: The name of the bucket for the files
        :param str root_path: The root path for all of the files

        """
        self._bucket_name = bucket_name
        self._root_path = root_path
        self._session = session.Session(profile_name=profile)
        self._client = self._session.client('s3')
        self._resource = self._session.resource('s3')

    def delete(self, file_name):
        """Delete a file from S3 by name

        :param str file_name: The file to delete

        """
        obj = self._resource.Object(self._bucket_name, self._key(file_name))
        obj.delete()
        LOGGER.debug('Deleted %s', file_name)

    def fetch(self, file_name):
        """Retrieve a file from S3 by name

        :param str file_name: The file to fetch
        :return: bytes

        """
        obj = self._resource.Object(self._bucket_name, self._key(file_name))
        response = obj.get()
        return response['Body']

    def upload(self, file_name, content):
        """Upload a file to S3, returning a pre-signed URL for accessing
        the file.

        :param str file_name: The name of the file
        :param bytes content: The file content
        :rtype: str

        """
        key = self._key(file_name)
        expiration = (datetime.datetime.utcnow() +
                      datetime.timedelta(seconds=TTL)).isoformat()
        try:
            self._client.put_object(ACL='authenticated-read',
                                    Body=content,
                                    Bucket=self._bucket_name,
                                    Expires=expiration,
                                    Key=key)
        except exceptions.ClientError as error:
            LOGGER.warning('Error putting value in bucket: %s', error)
            if error.response['Error']['Code'] == 'NoSuchBucket':
                self._create_bucket()
                return self.upload(file_name, content)
            raise error
        LOGGER.debug('Uploaded %s (%i bytes)', file_name, len(content))
        return self._client.generate_presigned_url(
            'get_object', Params={'Bucket': self._bucket_name, 'Key': key})

    def _create_bucket(self):
        self._client.create_bucket(Bucket=self._bucket_name)
        LOGGER.debug('Created bucket: %s', self._bucket_name)

    def _key(self, file_name):
        """Return the key to a file, prepending the root path to the key.

        :param str file_name: The name of the file
        :rtype: str

        """
        return '{0}/{1}'.format(self._root_path, file_name)
