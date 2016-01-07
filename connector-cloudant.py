import os
import json
import ibmiotf.application
import cloudant
import iso8601
import base64
from bottle import Bottle, template
import urllib
import argparse
import logging
from logging.handlers import RotatingFileHandler

class Server():

	def __init__(self, args):
		# Setup logging - Generate a default rotating file log handler and stream handler
		logFileName = 'connector-cloudant.log'
		fhFormatter = logging.Formatter('%(asctime)-25s %(name)-30s ' + ' %(levelname)-7s %(message)s')
		rfh = RotatingFileHandler(logFileName, mode='a', maxBytes=26214400 , backupCount=2, encoding=None, delay=True)
		rfh.setFormatter(fhFormatter)
		
		self.logger = logging.getLogger("server")
		self.logger.addHandler(rfh)
		self.logger.setLevel(logging.DEBUG)
		
		
		self.port = int(os.getenv('VCAP_APP_PORT', '8000'))
		self.host = str(os.getenv('VCAP_APP_HOST', 'localhost'))

		if args.bluemix == True:
			# Bluemix VCAP lookups
			application = json.loads(os.getenv('VCAP_APPLICATION'))
			service = json.loads(os.getenv('VCAP_SERVICES'))
			
			# IoTF
			self.options = ibmiotf.application.ParseConfigFromBluemixVCAP()
			
			# Cloudant
			self.dbUsername = service['cloudantNoSQLDB'][0]['credentials']['username']
			self.dbPassword = service['cloudantNoSQLDB'][0]['credentials']['password']
		else:
			self.options = ibmiotf.application.ParseConfigFile(args.config)
			self.dbUsername = args.cloudantUsername
			self.dbPassword = args.cloudantPassword
		
		
		self.dbName = self.options['org'] + "-events"
		
		# Bottle
		self._app = Bottle()
		self._route()
		
		# Init Cloudant client
		self._cloudantAccount = None
		self._cloudantLogin()
		self._cloudantDb = self._createDatabaseIfNotExists()
		
		# Init IOTF client
		self.client = ibmiotf.application.Client(self.options, logHandlers=[rfh])
	
	
	def _route(self):
		self._app.route('/', method="GET", callback=self._status)
	
	
	def myEventCallback(self, evt):
		#self.logger.info("%-33s%-30s%s" % (evt.timestamp.isoformat(), evt.device, evt.event + ": " + json.dumps(evt.data)))
		#self.logger.info(evt.data)
		
		# Create with a generated ID
		future = self._cloudantDb.post(params={
			'typeId': evt.deviceType,
			'deviceId': evt.deviceId,
			'eventId': evt.event,
			'timestamp': evt.timestamp.isoformat(),
			'data': evt.data,
			'format': evt.format,
			'payload': base64.encodestring(evt.payload).decode('ascii')
		})
		future.add_done_callback(self._eventRecordedCallback)
	
	
	def _eventRecordedCallback(self, future):
		response = future.result()
		#self.logger.info("%s - %s" % (response.url, response.status_code))
		if response.status_code not in [201, 202]:
			self.logger.info("Unexpected return code: %s - %s" % (response.url, response.status_code))
		
	
	def start(self):
		self.client.connect()
		self.client.deviceEventCallback = self.myEventCallback
		self.client.subscribeToDeviceEvents()
		self.logger.info("Serving at %s:%s" % (self.host, self.port))
		self._app.run(host=self.host, port=self.port)
	
	def stop(self):
		self.client.disconnect()
		
	def _status(self):
		return template('status', env_options=os.environ)


	# =============================================================================
	# Cloudant methods
	# =============================================================================
	def _cloudantLogin(self):
		self._cloudantAccount = cloudant.Account(self.dbUsername, async=True)
		future = self._cloudantAccount.login(self.dbUsername, self.dbPassword)
		login = future.result(10)
		assert login.status_code == 200


	def _createDatabaseIfNotExists(self):
		# Delete the Database (for a reset)
		# del self._cloudantAccount[self.dbName]
		
		db = self._cloudantAccount.database(self.dbName)
		# Allow up to 10 seconds
		response = db.get().result(10)
		if response.status_code == 200:
			self.logger.info(" * Database '%s' already exists (200)" % (self.dbName))
		elif response.status_code == 404:
			self.logger.info(" * Database '%s' does not exist (404), creating..." % (self.dbName))
			try:
				response = db.put().result(30)
			except TimeoutError:
				sys.exit(1)
			if response.status_code != 201:
				self.logger.info(" * Error creating database '%s' (%s)" % (self.dbName, response.status_code))
		else:
			self.logger.info(" * Unexpected status code (%s) when checking for existence of database '%s'" % (status, self.dbName))
			raise Exception("Unexpected status code (%s) when checking for existence of database '%s'" % (status, self.dbName))
		
		desiredDesignDocContent = {
			'byDevice': {
				'map': 'function(doc) { emit([doc.typeId, doc.deviceId, doc.timestamp], {"eventId": doc.eventId, "data": doc.data}); }'
			},
			'byTime': {
				'map': 'function(doc) { emit([doc.timestamp, doc.typeId, doc.deviceId], {"eventId": doc.eventId, "data": doc.data}); }'
			}
		}
		
		designDocName = "connector"
		doc = db.design(designDocName)
		response = doc.get().result(10)
		if response.status_code == 200:
			content = response.json()
			if "views" not in content or content["views"] != desiredDesignDocContent:
				self.logger.info("    * Design doc out of sync (%s:%s)" % (designDocName, "views"))
				content["views"] = desiredDesignDocContent
				doc.put(params=content).result(10)
			else:
				self.logger.info("    * Design doc already up to date (%s:%s)" % (designDocName, "views"))
		else:
			self.logger.info("    * Creating new design doc (%s:%s)" % (designDocName, "views"))
			doc.put(params={'language':'javascript', "views": desiredDesignDocContent}).result(10)
		return db



# Initialize the properties we need
parser = argparse.ArgumentParser()
parser.add_argument('-b', '--bluemix', required=False, action='store_true')
parser.add_argument('-c', '--config', required=False)
parser.add_argument('-u', '--cloudantUsername', required=False)
parser.add_argument('-p', '--cloudantPassword', required=False)

args, unknown = parser.parse_known_args()

server = Server(args)
server.start()