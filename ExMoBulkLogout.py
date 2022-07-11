"""
Created by dillonator

Copyright (c) 2018 Cisco and/or its affiliates.
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from lxml import etree
from requests import Session
from requests.auth import HTTPBasicAuth
from getpass import getpass

import zeep

from zeep import Client, Settings, Plugin, xsd
from zeep.transports import Transport
from zeep.exceptions import Fault
from progress.spinner import Spinner
import logging

# This script looks up all phones logged into Extension Mobility then prompts
# before logging them all out of Extension Mobility.


# Could use keyring instead to store username/passwords in Windows credential manager
cucmusername = input('Please enter your CUCM username: ')

amcucmpw = getpass(prompt='Please enter your CUCM password: ')

# Change this for your environment:
sessionCert = 'certs/[servercert].pem'
serverUrl = 'https://[hostname/ip]:8443/axl/'

# Change to true to enable output of request/response headers and XML
DEBUG = False

# The WSDL is a local file in the working directory, see README
WSDL_FILE = 'schema/AXLAPI.wsdl'

# This class lets you view the incoming and outgoing http headers and XML

class MyLoggingPlugin( Plugin ):

    def egress( self, envelope, http_headers, operation, binding_options ):

        # Format the request body as pretty printed XML
        xml = etree.tostring( envelope, pretty_print = True, encoding = 'unicode')

        print( f'\nRequest\n-------\nHeaders:\n{http_headers}\n\nBody:\n{xml}' )

    def ingress( self, envelope, http_headers, operation ):

        # Format the response body as pretty printed XML
        xml = etree.tostring( envelope, pretty_print = True, encoding = 'unicode')

        print( f'\nResponse\n-------\nHeaders:\n{http_headers}\n\nBody:\n{xml}' )

# The first step is to create a SOAP client session
session = Session()

# We avoid certificate verification by default
session.verify = False

# To enable SSL cert checking (recommended for production)
# place the CUCM Tomcat cert .pem file in the certs subfolder of the project 
# and uncomment the line below, comment out the line above

# session.verify = sessionCert

# Add Basic Auth credentials
session.auth = HTTPBasicAuth(cucmusername, amcucmpw)

# Create a Zeep transport and set a reasonable timeout value
transport = Transport( session = session, timeout = 10 )

# strict=False is not always necessary, but it allows zeep to parse imperfect XML
settings = Settings( strict = False, xml_huge_tree = True)

# If debug output is requested, add the MyLoggingPlugin callback
plugin = [ MyLoggingPlugin() ] if DEBUG else [ ]

# Create the Zeep client with the specified settings
client = Client( WSDL_FILE, settings = settings, transport = transport,
        plugins = plugin )

# Create the Zeep service binding to AXL at the specified CUCM
service = client.create_service( '{http://www.cisco.com/AXLAPIService/}AXLAPIBinding', serverUrl)


# Set up logging
log = "ExMoBulkLogout.log"
logging.basicConfig(filename='ExMoBulkLogout.log', level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S')


def _get_logged_In_Phone_List():
    loggedInPhoneList = []
    spinner = Spinner('Getting data... ')
    try:
        listPhoneResponse = service.listPhone(searchCriteria={'name': '%'},
                                               returnedTags={'name': '', 'currentProfileName': '', 'description': ''})
        listPhoneDict = listPhoneResponse['return']
        phoneList = listPhoneDict.phone
        for phone in phoneList:
            spinner.next()
            # Parse through list of phones and append to new list with only phones that have an ExMo profile logged in
            if phone.currentProfileName.uuid is not None:
                loggedInPhoneList.append(phone.name)
        return loggedInPhoneList
    except Fault as err:
        logging.error(cucmusername + ' ' + str(err))
        print(f'Zeep error: updatePhone: { err }')


def _log_out_phones(phonesLoggedIn):
    input('\nThere are ' + str(len(phonesLoggedIn)) + ' phones to be logged out, do you want to continue? Press Enter to continue.')
    try:
        logging.info(cucmusername + ' executed log out on the following phones' + phonesLoggedIn)
        for phone in phonesLoggedIn:
            service.doDeviceLogout(phone)
    except Fault as err:
        logging.error(cucmusername + ' ' + str(err))
        print(f'Zeep error: updatePhone: { err }')


phonesLoggedIn = _get_logged_In_Phone_List()
if len(phonesLoggedIn) == 0:
    input('\nNo phones logged into Extension Mobility. Press Enter.')   
else:
    _log_out_phones(phonesLoggedIn)

input('\nDone. Press enter to quit.')
