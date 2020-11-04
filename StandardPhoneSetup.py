"""AXL addUser/addLine/addPhone sample script, using the Zeep SOAP library
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
# This was tested and used on CUCM 11.5
# Note you must have the schema folder/files and CUCM .pem certs in the same location as script
# AXLAPI.wsdl
# AXLEnums.xsd
# AXLSoap.xsd

from lxml import etree
from requests import Session
from requests.auth import HTTPBasicAuth
from getpass import getpass

import keyring

from zeep import Client, Settings, Plugin, xsd
from zeep.transports import Transport
from zeep.exceptions import Fault
import sys
import time
import logging
from progress.spinner import Spinner
import re

# Use keyring to store username/passwords in Windows credential manager
resetCredentials = False
cucmusername = ''


def _setup_cucm_username():
    global cucmusername
    # Change username & password variables as you see fit
    cucmusername = keyring.get_password("username", "username")
    if cucmusername is None or cucmusername == "" or resetCredentials is True:
        print()
        print("No CUCM username found in local credential manager. Let's add it.")
        print()
        cucmusername = getpass(prompt="Please enter your CUCM username: Note: you will not see what's being typed: ")
        if cucmusername is None or cucmusername == "":
            print("No username entered. Goodbye.")
            sys.exit(1)
        else:
            keyring.set_password("username", "username", cucmusername)
            print('Added AM CUCM username to the local credential manager under "username."')


_setup_cucm_username()


cucmpassword = ''


def _setup_cucm_pw():
    global cucmpassword
    global resetCredentials
    cucmpassword = keyring.get_password("cucmpassword", "cucmpassword")
    if cucmpassword is None or cucmpassword == "" or resetCredentials is True:
        print()
        print("No CUCM password found in local credential manager. Let's add it.")
        print()
        cucmpassword = getpass(prompt="Please enter your CUCM password: ")
        if cucmpassword is None or cucmpassword == "":
            print("No password entered. Goodbye.")
            sys.exit(1)
        else:
            keyring.set_password("cucmpassword", "cucmpassword", cucmpassword)
            resetCredentials = False
            print('Added AM CUCM password to the local credential manager under "cucmpassword."')


_setup_cucm_pw()

# Set up logging
log = "standard.log"
logging.basicConfig(filename='standard.log', level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
logging.info(cucmusername + ' started running the script')

# CUCM Menu
sessionCert = ''
serverUrl = ''
userEnteredRegion = ''
locationMenu = {}
locationMenu["\n1"] = 'US'
locationMenu["2"] = 'Europe'
locationMenu["3"] = 'APAC'
while True:
    options = locationMenu.keys()
    for entry in options:
        print(entry, locationMenu[entry])

    selection = input("Please select regional CUCM you'd like to work with: ")
    if selection == "1":
        userEnteredRegion = 'US'
        sessionCert = 'us-cert-chain.pem'
        serverUrl = 'https://insertUSCUCMURL:8443/axl/'
        break
    elif selection == "2":
        userEnteredRegion = 'Europe'
        sessionCert = 'europe-cert-chain.pem'
        serverUrl = 'https://insertEuropeCUCMURL:8443/axl/'
        break
    elif selection == "3":
        userEnteredRegion = 'APAC'
        sessionCert = 'apac-cert-chain.pem'
        serverUrl = 'https://insertAPACCUCMURL.net:8443/axl/'
        break

# Location Menu
devicePoolName = None
locationName = None
callingSearchSpaceName = None
callForwardAll = None
externalMask = None
if userEnteredRegion == 'US':
    # US Location Menu
    # Set cluster specific variables
    commonDeviceConfigName = 'US-PHONES'
    softkeyTemplateName = 'Standard User'
    userLocale = 'English United States'
    routePartitionName = 'ALL_IPPhones'
    locationMenu = {}
    locationMenu["\n1"] = 'Location 1'
    locationMenu["2"] = 'Location 2'
    # you get the idea

    while True:
        options = locationMenu.keys()
        for entry in options:
            print(entry, locationMenu[entry])

        selection = input("Please select the location for this phone setup: ")
        if selection == "1":
            devicePoolName = 'LOCATION1_PHONES'
            locationName = 'LOCATION1'
            callingSearchSpaceName = 'LOCATION1_INTERNATIONAL'
            callForwardAll = {'callingSearchSpaceName': 'LOCATION1_CFA_CSS'}
            break
        elif selection == "2":
            devicePoolName = 'LOCATION2_PHONES'
            locationName = 'LOCATION2'
            callingSearchSpaceName = 'LOCATION2_LONG_DISTANCE'
            callForwardAll = {'callingSearchSpaceName': 'LOCATION2_CFA_CSS'}
            break
        # you get the idea

elif userEnteredRegion == 'Europe':
    # Europe location menu
    userLocale = None
    softkeyTemplateName = 'Standard User'
    routePartitionName = 'CLUSTER-DN'
    locationMenu = {}
    locationMenu["\n1"] = 'Denmark'
    locationMenu["2"] = 'Germany'
    # you get the idea

    while True:
        options = locationMenu.keys()
        for entry in options:
            print(entry, locationMenu[entry])

        selection = input("Please select the location for this phone setup: ")
        if selection == "1":
            devicePoolName = 'DENMARK-PHONES'
            commonDeviceConfigName = 'DENMARK-PHONES'
            locationName = 'DENMARK'
            callingSearchSpaceName = 'DEVICE-DENMARK-UNRESTRICTED'
            userLocale = 'Danish Denmark'
            callForwardAll = {'callingSearchSpaceName': 'CW-INTERNAL'}
            print('\nDenmark set to allow internal forwarding only (Forward All CSS = CW-INTERNAL)')
            # networkLocale = 'Denmark' # shouldn't need this as it's set on device pool
            break
        elif selection == "2":
            devicePoolName = 'GERMANY-PHONES'
            commonDeviceConfigName = 'GERMANY-PHONES'
            locationName = 'GERMANY'
            callingSearchSpaceName = 'DEVICE-GERMANY-UNRESTRICTED'
            userLocale = 'German Germany'
            callForwardAll = {'callingSearchSpaceName': 'CW-INTERNAL'}
            print('\nDiamant set to allow internal forwarding only (Forward All CSS = CW-INTERNAL)')
            break
        # you get the idea

elif userEnteredRegion == 'APAC':
    # APAC menu for agent location
    userLocale = None
    softkeyTemplateName = 'CUSTOM User'
    routePartitionName = 'SYSTEM-CLUSTER-DN'
    locationMenu = {}
    locationMenu["\n1"] = 'Australia'
    locationMenu["2"] = 'Japan'
    # you get the idea

    while True:
        options = locationMenu.keys()
        for entry in options:
            print(entry, locationMenu[entry])

        selection = input("Please select the location for this phone setup: ")
        if selection == "1":
            devicePoolName = 'AUSTRALIA-PHONES'
            commonDeviceConfigName = 'AUSTRALIA-PHONES'
            locationName = 'AUSTRALIA'
            callingSearchSpaceName = 'AUSTRALIA-UNRESTRICTED'
            userLocale = 'English United States'
            softkeyTemplateName = 'CUSTOM AUSTRALIA User'
            callForwardAll = {'callingSearchSpaceName': 'SYSTEM-CW-INTERNAL'}
            print('\nAustralia set to allow internal forwarding only (Forward All CSS = SYSTEM-CW-INTERNAL)')
            break
        elif selection == "2":
            devicePoolName = 'JAPAN-PHONES'
            commonDeviceConfigName = 'JAPAN-PHONES'
            locationName = 'JAPAN'
            callingSearchSpaceName = 'JAPAN-UNRESTRICTED'
            userLocale = 'Japanese Japan'
            callForwardAll = {'callingSearchSpaceName': 'SYSTEM-CW-INTERNAL'}
            print('\nJapan set to allow internal forwarding only (Forward All CSS = SYSTEM-CW-INTERNAL)')
            break


def _get_Phone_Mac_Address():
    global phoneMac
    global deskPhoneDeviceName
    phoneMac = input("\nPlease enter the MAC address of the desk phone (Quit if there's no desk phone): ")
    if re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", phoneMac.lower()):
        # regex replacement of - & :
        phoneMac = re.sub(r'[:-]', '', phoneMac)
        deskPhoneDeviceName = 'SEP' + phoneMac.upper()
    else:
        print('Invalid MAC address, please try again.')
        _get_Phone_Mac_Address()


# Get Prereqs / input data
phoneUsername = input("\nPlease enter the username of the person for the phone setup: ")
phoneExt = input("\nPlease enter the extension for the phone setup: ")
# Menu for type of phone build Jabber/Deskphone/CIPC etc.
userEnteredPhoneModel = ''
jabberOnly = False
deskPhoneOnly = False
phoneMac = None
deskPhoneDeviceName = None
phoneBuildMenu = {}
phoneBuildMenu["\n1"] = 'Desk Phone Only'
phoneBuildMenu["2"] = 'Jabber Only'
phoneBuildMenu["3"] = 'Desk Phone & Jabber'
while True:
    options = phoneBuildMenu.keys()
    for entry in options:
        print(entry, phoneBuildMenu[entry])
    selection = input("Please select the type of phone build: ")
    if selection == "1":
        deskPhoneOnly = True
        userEnteredPhoneModel = input("\nPlease enter the model of the desk phone (e.g. 7942): ")
        # replaced simple input with function to validate mac address
        _get_Phone_Mac_Address()
        break
    elif selection == "2":
        jabberOnly = True
        break
    elif selection == "3":
        userEnteredPhoneModel = input("\nPlease enter the model of the desk phone (e.g. 7942): ")
        phoneMac = input("\nPlease enter the MAC address of the desk phone (Quit if there's no desk phone): ")
        deskPhoneDeviceName = 'SEP' + phoneMac
        break


def _setup_connection():
    # Setup SOAP/AXL/HTTPS Connection
    global service
    # Change to true to enable output of request/response headers and XML
    DEBUG = False

    # The WSDL is a local file in the working directory, see README
    WSDL_FILE = 'schema/AXLAPI.wsdl'

    # This class lets you view the incoming and outgoing http headers and XML

    class MyLoggingPlugin(Plugin):

        def egress(self, envelope, http_headers, operation, binding_options):

            # Format the request body as pretty printed XML
            xml = etree.tostring(envelope, pretty_print=True, encoding='unicode')

            print(f'\nRequest\n-------\nHeaders:\n{http_headers}\n\nBody:\n{xml}')

        def ingress(self, envelope, http_headers, operation):

            # Format the response body as pretty printed XML
            xml = etree.tostring(envelope, pretty_print=True, encoding='unicode')

            print(f'\nResponse\n-------\nHeaders:\n{http_headers}\n\nBody:\n{xml}')


    # The first step is to create a SOAP client session
    session = Session()

    # We avoid certificate verification by default
    # session.verify = False

    # To enabled SSL cert checking (recommended for production)
    # place the CUCM Tomcat cert .pem file in the root of the project
    # and uncomment the line below

    session.verify = sessionCert

    # Add Basic Auth credentials
    session.auth = HTTPBasicAuth(cucmusername, cucmpassword)

    # Create a Zeep transport and set a reasonable timeout value
    transport = Transport(session=session, timeout=10)

    # strict=False is not always necessary, but it allows zeep to parse imperfect XML
    settings = Settings(strict=False, xml_huge_tree=True)

    # If debug output is requested, add the MyLoggingPlugin callback
    plugin = [MyLoggingPlugin()] if DEBUG else [ ]

    # Create the Zeep client with the specified settings
    client = Client(WSDL_FILE, settings=settings, transport=transport,
            plugins=plugin)

    # FUTURE create CUCM chooser menu

    # Create the Zeep service binding to AXL at the specified CUCM
    service = client.create_service('{http://www.cisco.com/AXLAPIService/}AXLAPIBinding', serverUrl)


_setup_connection()


def _check_for_existing_setup():
    global resetCredentials
    global associatedDevices
    # Find out if there's an existing phone/extension and if it's associated with the line
    try:
        lineResp = service.getLine(pattern=phoneExt, routePartitionName=routePartitionName)
        # Unpack line dict and get associatedDevices. Format: userDetails = rawresp['return'].user
        associatedDevices = lineResp['return'].line.associatedDevices
    except Fault as err:
        if str(err) == 'Item not valid: The specified Line was not found':
            # Extension doesn't exist either error out or ask to create
            # print(f'Zeep error: getLine: { err }')
            logging.warning(cucmusername + ' Extension does not exist')
            userResp = input('\nThis extension does not exist, would you like to create? (y/n) ')
            if userResp == 'y' or userResp == 'Y':
                # FUTURE create ext.
                input('\nCode to create new extension has not been implemented, exiting.')
                sys.exit(1)
            else:
                input('\nPress Enter to quit.')
                sys.exit(1)
        elif str(err) == 'Unknown fault occured':
            # Wrong credentials?
            logging.error(cucmusername + ' ' + str(err))
            print(f'Zeep error: getLine: { err }')
            resetCredentailMenu = {}
            resetCredentailMenu["\n1"] = 'Try username & password again'
            resetCredentailMenu["2"] = 'Quit'
            while True:
                options = resetCredentailMenu.keys()
                for entry in options:
                    print(entry, resetCredentailMenu[entry])
                selection = input("Error authenticating or unknown error. Choose an option above: ")
                if selection == "1":
                    resetCredentials = True
                    _setup_cucm_username()
                    _setup_cucm_pw()
                    _setup_connection()
                    _check_for_existing_setup()
                    break
                elif selection == "2":
                    sys.exit(1)
                    break
        else:
            logging.error(cucmusername + ' ' + str(err))
            print(f'Zeep error: getLine: { err }')
            input('\nCheck the error above and consult admin if needed, exiting.')
            sys.exit(1)


_check_for_existing_setup()

# Assume extension exists and continuing to create phone/device profile
# Ask if you want to blow it away or quit
if associatedDevices is None or associatedDevices == "":
    print('\nNo devices associated with this line, continuing setup...')
else:

    print(associatedDevices)
    existingDeviceMenu = {}
    existingDeviceMenu["\n1"] = 'CONTINUE: I am adding a device to an existing user that already has a phone.'
    existingDeviceMenu["2"] = 'DELETE: Remove or re-use this phone (This will delete all phones above. WARNING: All previous configuration will be lost.)'
    existingDeviceMenu["3"] = 'QUIT (check the device name/mac address or clean things up manually in CUCM.)'
    while True:
        options = existingDeviceMenu.keys()
        for entry in options:
            print(entry, existingDeviceMenu[entry])
        selection = input('A device already exists with this extension. What would you like to do? ')
        if selection == "1":
            break
        # need to test this code
        elif selection == "2":
            service.removePhone(name=associatedDevices)
            print('Deleted these devices:')
            print(associatedDevices)
            break
        elif selection == "3":
            sys.exit(1)
            break

# Force LDAP Sync to pull name instead of prompting for them
try:
    resp = service.doLdapSync(name='LDAP', sync='true')
except Fault as err:
    logging.error(cucmusername + ' ' + str(err))
    print(f'Zeep error: doLdapSync: { err }')
    input('\n Press Enter to quit.')
    sys.exit(1)
# Loop and get status of LDAP sync before proceeding. Wait 1 second or it gets caught before complete
spinner = Spinner('LDAP Syncing. This may take 1-2 minutes... ')
time.sleep(1)
ldapSyncStatus = ''
while ldapSyncStatus != 'Sync is performed successfully':
    try:
        resp = service.getLdapSyncStatus(name='LDAP')
        ldapSyncStatus = resp['return']
    except Fault as err:
        logging.error(cucmusername + ' ' + str(err))
        print(f'Zeep error: doLdapSync: { err }')
    spinner.next()
    time.sleep(1)
print(' LDAP Sync Successful...\n')

# Execute the getUser request
try:
    getUserResponse = service.getUser(userid=phoneUsername)
    userDetails = getUserResponse['return'].user
    phoneLname = userDetails.lastName
    phoneFname = userDetails.firstName
except Fault as err:
    logging.error(cucmusername + ' ' + str(err))
    print(f'Zeep error: getUser: { err }')
    input('\n Press Enter to quit.')
    sys.exit(1)

# Normalize some data
jabberDeviceName = 'csf' + phoneUsername
phoneDescription = phoneFname + ' ' + phoneLname + ' - ' + phoneExt
phoneDisplay = phoneLname + ', ' + phoneFname[0]
phoneModel = 'Cisco ' + userEnteredPhoneModel

logging.info(cucmusername + ' setting up ' + phoneUsername + ' ' + phoneDescription + ' in ' + locationName)
input('Continue phone build for ' + phoneDescription + ' in ' + locationName + ' ? (Press Ctrl + C to quit. Press Enter to continue...)')


def _setup_Jabber():
    # Create the data for adding Jabber, associating the Line
    phone = {
        'name': jabberDeviceName,
        'description': phoneDescription,
        'product': 'Cisco Unified Client Services Framework',
        'model': 'Cisco Unified Client Services Framework',
        'class': 'Phone',
        'protocol': 'SIP',
        'protocolSide': 'User',
        'devicePoolName': devicePoolName,
        'commonDeviceConfigName': commonDeviceConfigName,
        'phoneTemplateName': 'Standard Client Services Framework',
        'commonPhoneConfigName': 'Standard Common Phone Profile',
        'locationName': locationName,
        'useTrustedRelayPoint': 'Default',
        'builtInBridgeStatus': 'Default',
        'deviceMobilityMode': 'Default',
        'callingSearchSpaceName': callingSearchSpaceName,
        'retryVideoCallAsAudio': 'true',
        'allowCtiControlFlag': 'true',
        'hlogStatus': 'On',
        'packetCaptureMode': 'None',
        'certificateOperation': 'No Pending Operation',
        'enableExtensionMobility': 'true',
        # Add line
        'lines': {
            'line': [
                {
                    'index': 1,
                    'label': phoneDescription,  # Line text label
                    'dirn': {
                        'pattern': phoneExt,
                        'routePartitionName': routePartitionName,
                    },
                    'display': phoneDisplay,
                    'displayAscii': phoneDisplay,
                    'e164Mask': externalMask,  # Used in specific locations
                    'associatedEndusers': {
                        'enduser': [
                            {
                                'userId': phoneUsername
                            }
                        ]
                    }
                }
            ]
        },
        'securityProfileName': 'Cisco Unified Client Services Framework - Standard SIP Non-Secure Profile'
    }
    # Execute the addPhone request
    try:
        resp = service.addPhone(phone)
        logging.info(cucmusername + ' created Jabber device ' + jabberDeviceName)

    except Fault as err:
        logging.error(cucmusername + ' ' + str(err))
        print(f'Zeep error: addPhone: { err }')
        input('\n Press Enter to quit.')
        sys.exit(1)
    # print('\naddPhone response:\n')
    # print(resp, '\n')
    input('Jabber creation complete. Press Enter to continue...')

    # Execute the updateLine request
    try:
        resp = service.updateLine(
            pattern=phoneExt,
            routePartitionName=routePartitionName,
            alertingName=phoneDisplay,
            asciiAlertingName=phoneDisplay,
            description=phoneDescription,
            callForwardAll=callForwardAll
        )

    except Fault as err:
        logging.error(cucmusername + ' ' + str(err))
        print(f'Zeep error: updateLine: { err }')
        input('\n Press Enter to quit.')
        sys.exit(1)
    # print('\nupdateLine response:\n')
    # print(resp, '\n')
    input('Line Updated. Press Enter to continue...')


def _setup_desk_phone():
    # may need to add more models to diferentiate SIP/SCCP
    if phoneModel.startswith('Cisco 78') or phoneModel.startswith('Cisco 88'):
        protocol = 'SIP'
        securityProfileName = phoneModel + ' - Standard SIP Non-Secure Profile'
    else:
        protocol = 'SCCP'
        securityProfileName = None
    if userEnteredPhoneModel == '7942' or userEnteredPhoneModel == '7962':
        phoneTemplateName = 'Standard ' + userEnteredPhoneModel + 'G ' + protocol
    else:
        phoneTemplateName = 'Standard ' + userEnteredPhoneModel + ' ' + protocol
    phone = {
        'name': deskPhoneDeviceName,
        'description': phoneDescription,
        'product': phoneModel,
        'model': phoneModel,
        'class': 'Phone',
        'protocol': protocol,
        'protocolSide': 'User',
        'devicePoolName': devicePoolName,
        'commonDeviceConfigName': commonDeviceConfigName,
        'phoneTemplateName': phoneTemplateName,
        'softkeyTemplateName': softkeyTemplateName,
        'commonPhoneConfigName': 'Standard Common Phone Profile',
        'locationName': locationName,
        'useTrustedRelayPoint': 'Default',
        'builtInBridgeStatus': 'Default',
        'deviceMobilityMode': 'Default',
        'callingSearchSpaceName': callingSearchSpaceName,
        'retryVideoCallAsAudio': 'true',
        'allowCtiControlFlag': 'true',
        'hlogStatus': 'On',
        'packetCaptureMode': 'None',
        'certificateOperation': 'No Pending Operation',
        'enableExtensionMobility': 'true',
        'securityProfileName': securityProfileName,
        # Add line
        'lines': {
            'line': [
                {
                    'index': 1,
                    'label': phoneDescription,  # Line text label
                    'dirn': {
                        'pattern': phoneExt,
                        'routePartitionName': routePartitionName,
                    },
                    'display': phoneDisplay,
                    'displayAscii': phoneDisplay,
                    'e164Mask': externalMask,  # Used in specific locations
                    'associatedEndusers': {
                        'enduser': [
                            {
                                'userId': phoneUsername
                            }
                        ]
                    }
                }
            ]
        }
    }

    # Execute the addPhone request
    try:
        resp = service.addPhone(phone)
        logging.info(cucmusername + ' created desk phone ' + deskPhoneDeviceName + ' ' + userEnteredPhoneModel)
        # TODO Future add handling for a device that already exists
        # Could not insert new row - duplicate value in a UNIQUE INDEX column (Unique Index:)
    except Fault as err:
        logging.error(cucmusername + ' ' + str(err))
        print(f'Zeep error: addPhone: { err }')
        input('\n Press Enter to quit.')
        sys.exit(1)
    # print('\naddPhone response:\n')
    # print(resp, '\n')
    input('Desk phone creation complete. Press Enter to continue...')

    # Execute the updateLine request
    try:
        resp = service.updateLine(
            pattern=phoneExt,
            routePartitionName=routePartitionName,
            alertingName=phoneDisplay,
            asciiAlertingName=phoneDisplay,
            description=phoneDescription,
            callForwardAll=callForwardAll
        )

    except Fault as err:
        logging.error(cucmusername + ' ' + str(err))
        print(f'Zeep error: updateLine: { err }')
        input('\n Press Enter to quit.')
        sys.exit(1)
    # print('\nupdateLine response:\n')
    # print(resp, '\n')
    input('Line Updated. Press Enter to continue...')


def _update_End_User():
    # LDAP sync should have occured above
    # Set data for UpdateUser Request (only variables with multiple values)

    primaryExtension = {
        'pattern': phoneExt,
        'routePartitionName': routePartitionName
    }
    associatedGroups = {
        'userGroup': [
            {'name': 'Standard CCM End Users'},
            {'name': 'Standard CTI Enabled'}
        ]
    }
    if deskPhoneOnly:
        # Get existing data and append or it will wipe out existing associations
        try:
            resp = service.getUser(userid=phoneUsername)
            userDetails = resp['return'].user
            currentAssociatedDeviceList = userDetails.associatedDevices
        except Fault as err:
            print(f'Zeep error: getUser: { err }')
            input('\n Press Enter to quit.')
            sys.exit(1)
        # Append desk phone to list
        if currentAssociatedDeviceList is None:
            updatedAssociatedDevices = {
                'device': deskPhoneDeviceName
            }
        else:
            unpackedAssociatedDevices = currentAssociatedDeviceList.device
            unpackedAssociatedDevices.append(deskPhoneDeviceName)
            updatedAssociatedDevices = {
                'device': unpackedAssociatedDevices
            }
    elif jabberOnly:
        # Get existing data and append or it will wipe out existing associations
        try:
            resp = service.getUser(userid=phoneUsername)
            userDetails = resp['return'].user
            currentAssociatedDeviceList = userDetails.associatedDevices
        except Fault as err:
            print(f'Zeep error: getUser: { err }')
            input('\n Press Enter to quit.')
            sys.exit(1)
        # Append jabber to list
        if currentAssociatedDeviceList is None:
            updatedAssociatedDevices = {
                'device': jabberDeviceName
            }
        else:
            unpackedAssociatedDevices = currentAssociatedDeviceList.device
            unpackedAssociatedDevices.append(jabberDeviceName)
            updatedAssociatedDevices = {
                'device': unpackedAssociatedDevices
            }
    else:
        # Get existing data and append or it will wipe out existing associations
        try:
            resp = service.getUser(userid=phoneUsername)
            userDetails = resp['return'].user
            currentAssociatedDeviceList = userDetails.associatedDevices
        except Fault as err:
            print(f'Zeep error: getUser: { err }')
            input('\n Press Enter to quit.')
            sys.exit(1)
        # Append jabber to list
        if currentAssociatedDeviceList is None:
            updatedAssociatedDevices = {
                'device': [
                    jabberDeviceName,
                    deskPhoneDeviceName
                ]
            }
        else:
            unpackedAssociatedDevices = currentAssociatedDeviceList.device
            unpackedAssociatedDevices.append(deskPhoneDeviceName)
            unpackedAssociatedDevices.append(jabberDeviceName)
            updatedAssociatedDevices = {
                'device': unpackedAssociatedDevices
            }
    # Execute update end user (1st time)
    if deskPhoneOnly:
        try:
            resp = service.updateUser(
                    userid=phoneUsername,
                    userLocale=userLocale,
                    homeCluster=True,
                    associatedDevices=updatedAssociatedDevices,
                    enableCti=True,
                    associatedGroups=associatedGroups
                    )
            logging.info(cucmusername + ' first pass updated end user ' + phoneUsername)
        except Fault as err:
            logging.error(cucmusername + ' ' + str(err))
            print(f'Zeep error: updateUser: { err }')
            input('\n Press Enter to quit.')
            sys.exit(1)
    else:
        try:
            resp = service.updateUser(
                userid=phoneUsername,
                userLocale=userLocale,
                homeCluster=True,
                imAndPresenceEnable=True,
                associatedDevices=updatedAssociatedDevices,
                enableCti=True,
                associatedGroups=associatedGroups
                )
            logging.info(cucmusername + ' first pass updated end user ' + phoneUsername)
        except Fault as err:
            logging.error(cucmusername + ' ' + str(err))
            print(f'Zeep error: updateUser: { err }')
            input('\n Press Enter to quit.')
            sys.exit(1)
        # print('\nupdateUser response:\n')
        # print(resp, '\n')

    # Execute update end user (2nd time)
    try:
        resp = service.updateUser(
            userid=phoneUsername,
            # Need to update after phone/Jabber is associated
            primaryExtension=primaryExtension,
            )
        logging.info(cucmusername + ' second pass updated end user ' + phoneUsername)
    except Fault as err:
        logging.error(cucmusername + ' ' + str(err))
        print(f'Zeep error: updateUser: { err }')
        input('\n Press Enter to quit.')
        sys.exit(1)
    print('End User Updated...\n')


def _update_Desk_Phone_Owner():
    try:
        resp = service.updatePhone(
            name=deskPhoneDeviceName,
            ownerUserName=phoneUsername
            )
        logging.info(cucmusername + ' updated desk phone ' + deskPhoneDeviceName + ' owner to ' + phoneUsername)
    except Fault as err:
        logging.error(cucmusername + ' ' + str(err))
        print(f'Zeep error: updatePhone: { err }')
        input('\n Press Enter to quit.')
        sys.exit(1)
    print('Desk Phone owner updated...\n')


def _update_Jabber_Owner():
    try:
        resp = service.updatePhone(
            name=jabberDeviceName,
            ownerUserName=phoneUsername
            )
        logging.info(cucmusername + ' updated jabber ' + jabberDeviceName + ' owner to ' + phoneUsername)
    except Fault as err:
        logging.error(cucmusername + ' ' + str(err))
        print(f'Zeep error: updatePhone: { err }')
        input('\n Press Enter to quit.')
        sys.exit(1)
    print('Jabber owner updated...\n')


# EXECUTE!
if deskPhoneOnly:
    _setup_desk_phone()
    _update_End_User()
    _update_Desk_Phone_Owner()
elif jabberOnly:
    _setup_Jabber()
    _update_End_User()
    _update_Jabber_Owner()
else:
    _setup_desk_phone()
    _setup_Jabber()
    _update_End_User()
    _update_Desk_Phone_Owner()
    _update_Jabber_Owner()

logging.info(cucmusername + ' succesfully reached end of script')
input(
    'Complete. Do the following manual tasks where applicable:'
    '\n1:Setup voicemail (import from LDAP using UCXN GUI)'
    '\nPress Enter to quit.')
