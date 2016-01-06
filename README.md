#IoTF Cloudant Connector

## Standalone Execution
```bash
$ python record-cloudant.py -c app.cfg -u myCloudantUsername -p myCloudantPassword
Bottle v0.12.8 server starting up (using WSGIRefServer())...
Listening on http://localhost:8000/
Hit Ctrl-C to quit.
```


----


##Bluemix Deployment

###Bluemix Command-line Prerequisites
+ GitHub client [git](https://github.com/)
+ Cloud Foundry CLI [cf](https://github.com/cloudfoundry/cli/releases)
+ Bluemix account [register](https://bluemix.net/registration)

###Get the sample source code
```bash
$ git clone https://github.com/ibm-iotf/connector-cloudant.git
```

###Create a new application
```bash
$ cf push <app_name> --no-start
```

###Optionally, create the required services
```bash
$ cf create-service iotf-service iotf-service-free <iotf_instance_name>
$ cf create-service cloudantNoSQLDB Shared <cloudant_instance_name>
```

### Bind the services to your application
```bash
$ cf bind-service <app_name> <iotf_instance_name>
$ cf bind-service <app_name> <cloudant_instance_name>
```

###Start the application
```bash
$ cf start <app_name>
```

###Launch your application

Open http://&lt;app_name&gt;.mybluemix.net/ in a browser


