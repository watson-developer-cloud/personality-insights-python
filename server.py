#
# Copyright 2014 IBM Corp. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
## -*- coding: utf-8 -*-

import os
import cherrypy
import requests
import json
from mako.template import Template
from mako.lookup import TemplateLookup


class UserModelingService:
    """Wrapper on the User Modeling service"""

    def __init__(self, vcapServices):
        """
        Construct an instance. Fetches service parameters from VCAP_SERVICES
        runtime variable for Bluemix, or it defaults to local URLs.
        """

        # Local variables
        self.url = "<url>"
        self.username = "<username>"
        self.password = "<password>"

        if vcapServices is not None:
            print("Parsing VCAP_SERVICES")
            services = json.loads(vcapServices)
            svcName = "user_modeling"
            if svcName in services:
                print("User modeling service found!")
                svc = services[svcName][0]["credentials"]
                self.url = svc["url"]
                self.username = svc["username"]
                self.password = svc["password"]
            else:
                print("ERROR: The User Modeling service was not found")

    # Builds the content object to send to User Modeling API from a
    # single piece of text
    def _formatPOSTData(self, text):
        return {
            'contentItems': [{
                'userid': 'dummy',
                'id': 'dummyUuid',
                'sourceid': 'freetext',
                'contenttype': 'text/plain',
                'language': 'en',
                'content': text
            }]
        }

    def getProfile(self, text):
        """Returns the profile by doing a POST to /v2/profile with text"""

        if self.url is None:
            raise Exception("No User Modeling service is bound to this app")

        data = self._formatPOSTData(text)
        response = requests.post(self.url + "api/v2/profile",
                          auth=(self.username, self.password),
                          headers = {"content-type": "application/json"},
                          data=json.dumps(data)
                          )
        try:
            return json.loads(response.text)
        except:
            raise Exception("Error processing the request, HTTP: %d" % response.status_code)


class DemoService(object):
    """
    REST service/app. Since we just have 1 GET and 1 POST URLs,
    there is not even need to look at paths in the request.
    This class implements the handler API for cherrypy library.
    """
    exposed = True

    def __init__(self, service):
        self.service = service
        self.defaultContent = None
        try:
            contentFile = open("mobidick.txt", "r")
            self.defaultContent = contentFile.read()
        except Exception as e:
            print "ERROR: couldn't read mobidick.txt: %s" % e
        finally:
            contentFile.close()

    def GET(self):
        """Shows the default page with sample text content"""
        return lookup.get_template("index.html").render(content=self.defaultContent)


    def POST(self, text=None):
        """
        Send 'text' to the User Modeling API
        and return the response.
        """
        try:
            profileJson = self.service.getProfile(text)
            return json.dumps(profileJson)
        except Exception as e:
            print "ERROR: %s" % e
            return str(e)


if __name__ == '__main__':
    lookup = TemplateLookup(directories=["templates"])

    # Get host/port from the Bluemix environment, or default to local
    HOST_NAME = os.getenv("VCAP_APP_HOST", "127.0.0.1")
    PORT_NUMBER = int(os.getenv("VCAP_APP_PORT", "3000"))
    cherrypy.config.update({
        "server.socket_host": HOST_NAME,
        "server.socket_port": PORT_NUMBER,
    })

    # Configure 2 paths: "public" for all JS/CSS content, and everything
    # else in "/" handled by the DemoService
    conf = {
        "/": {
            "request.dispatch": cherrypy.dispatch.MethodDispatcher(),
            "tools.response_headers.on": True,
            "tools.staticdir.root": os.path.abspath(os.getcwd())
        },
        "/public": {
            "tools.staticdir.on": True,
            "tools.staticdir.dir": "./public"
        }
    }

    # Create the User Modeling Wrapper
    userModeling = UserModelingService(os.getenv("VCAP_SERVICES"))

    # Start the server
    print("Listening on %s:%d" % (HOST_NAME, PORT_NUMBER))
    cherrypy.quickstart(DemoService(userModeling), "/", config=conf)
