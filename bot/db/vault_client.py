import hvac
import logging
import json
import os


class VaultClient(object):
    BASE_FILE_PATH = "/opt/xebialabs/slack-xlrelease-app/log/.secret"
    BASE_PATH = "secret"

    def __init__(self, url='http://localhost:8200', token=None):
        self.logger = logging.getLogger(__name__)
        token = os.environ.get("VAULT_TOKEN")
        url = os.environ.get("VAULT_URL")
        self.logger.info("url = %s" % url )
        self.logger.info("token = %s" % token)
        self.vault_client = hvac.Client(url=url, token=token)

    def testVault( self ):
        try:
            self.vault_client.write("{}/{}".format(self.BASE_PATH, "testVault"), value="testVault")
            record = self.vault_client.read("{}/{}".format(self.BASE_PATH, "testVault"))
            #self.set_secret(path="testVault", secret="testVault")
            #record = self.get_secret(path="testVault")
            if record['data']['value'] != "testVault":
                self.logger.error("Vault Test Failed %s" % record)
                raise Exception("Vault Test Failed")
            return "SUCCESS"
        except Exception as ex:
            self.logger.error( ex )
            return "FAILED"

    def set_secret(self, path=None, secret=None):
        self.vault_client.write("{}/{}".format(self.BASE_PATH, path), value=secret)

    def get_secret(self, path=None):
        try:
            record = self.vault_client.read("{}/{}".format(self.BASE_PATH, path))
        except:
            self.logger.error("Secret for %s/%s MISSING" % ( self.BASE_PATH, path ))
            self.set_secret( path=path, secret="" )
            record = ""
        return record["data"]["value"] if record else None
        #return record["value"] if record else None

    def mkdir_p(self, path):
        try:
            os.makedirs(path)
            os.chmod(path , 0o700)
        except OSError as exc: # Python >2.5
            self.logger.info( exc )

    def safe_open_w(self, path):
        ''' Open "path" for writing, creating any parent directories as needed.
        '''
        self.mkdir_p(os.path.dirname(path))
        return open(path, 'w')
