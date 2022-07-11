# cucm-provisoning
ExMoBulkLogout.py can be used for logging out all phones from extension mobility.

Python/AXL/Zeep script for phone build automation.
Tested on CUCM 11.5

You will need to update the URLs and put certificates in the correct location along side the script. You can get the AXL files & schema here:

    From the CUCM Administration UI, download the 'Cisco AXL Tookit' from Applications / Plugins

    Unzip the kit, and navigate to the schema/current folder

    Copy the three WSDL files to the schema/ directory of this project: AXLAPI.wsdl, AXLEnums.xsd, AXLSoap.xsd


There are menus to choose from 3 separate CUCM clusters. Beneath that is a menu to build out each location within the cluster.

Data was scrubbed out of production script, so search for "insert" and "location" to customize for your needs.

Started from this template:
https://github.com/CiscoDevNet/axl-python-zeep-samples/blob/master/axl_add_User_Line_Phone.py
