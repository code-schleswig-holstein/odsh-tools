# This Python file uses the following encoding: utf-8
from ckanapi import RemoteCKAN, NotFound, CKANAPIError 
import xlrd
import csv
import sys
import os
import datetime
import logging
if sys.version_info[0] == 2:
    import urllib2
elif sys.version_info[0] == 3:  # >=Python3.1
    import urllib

##########################
#     Initialisation     #
##########################

# HTTP or HTTPS?
HTTPS = False
# The api-key can be found at user-details after login.
# (User details are not shown anymore in the ODSH design)
# HOST = "134.100.14.144"
# api_key = '2177559e-29be-41a9-99c2-626d4be233d9'
HOST = "10.61.47.219"
api_key = 'fd49708b-91b3-492a-bdb0-93fa4c8e4d39'
OWNER_ORG = 'landesamt-fuer-soziale-dienste'
PATH = "/home/ckanuser/lasdsh_log"
# FILENAME = "Metadatentabelle_LAsDSH_2018-09-18.xlsx"
FILENAME = "Metadatentabelle_Test.csv"
CSV_FILE_DELIMITER = '\t'
RESOURCE_PATH = PATH
now = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d_%H:%M:%S")
LOGFILE_NAME = "report_" + now + ".log"

# VALID_KEYS is a static list, as the mapping of these keys to the CKAN-fields
# is fixed. If entries in this list are changed, also the mapping must be changed.
VALID_KEYS = [
 "Titel",
 "Beschreibung",
 "Lizenz",
 "Text für Namensnennung",
 "Download-URL",
 "Zugriffs-URL",
 "Veröffentlichungsdatum",
 "Kategorie",
 "Schlagwörte",
 "Räumliche Ausdehnung",
 "Zeitraum Beginn",
 "Zeitraum Ende"]

# Valid licence keys correspond to entries in the spreadsheet file.
# Those are mapped to the ids from licences.json.
VALID_LICENCES = {
 'dl-by-de/2.0': 'http://dcat-ap.de/def/licenses/dl-by-de/2.0',
 'dl-zero-de/2.0': 'http://dcat-ap.de/def/licenses/dl-zero-de/2.0'
}

r_ckan = RemoteCKAN('http://' + HOST, apikey=api_key)

# GROUPS_LIST and LICENSE_LIST contains all valid entrys that can be found
# within the already existing entries. Previously unknown entries will not be
# accepted here, they have to be initialised in CKAN first. (Like OWNER_ORG)
try:
    GROUPS_LIST = r_ckan.action.group_list()
except ConnectionError as e:
    print("Could not connect to CKAN: " % i + str(e))
    sys.exit()


##########################
#  Function definitions  #
##########################

# Checks for typos in keys
def check_keys(in_list):
    try:
        for i, elem in enumerate(in_list):
            if elem not in VALID_KEYS:
                raise ValueError(
                  "'" + elem + "' is an unknown key in column " + str(i)
                  + ". If this key should be accepted, please put it in the list of "
                  + "valid keys and set the mapping to a valid CKAN dataset field.")
    except ValueError as e:
        print(str(e))
        sys.exit()


def create_xls_dict(keys, vals, datemode):
    result = {}
    for i, item in enumerate(keys):
        try:
            if vals[i].ctype == xlrd.XL_CELL_TEXT or vals[i].ctype == xlrd.XL_CELL_NUMBER:
                if item == "Zeitraum Beginn" or item == "Zeitraum Ende":
                    result[item] = datetime.datetime.strptime(
                      vals[i].value, "%Y-%m-%d").isoformat()
                else:
                    result[item] = vals[i].value
            elif vals[i].ctype == xlrd.XL_CELL_DATE:
                result[item] = datetime.datetime.strptime(
                  str(xlrd.xldate_as_tuple(vals[i].value,
                      datemode)), "(%Y, %m, %d, %H, %M, %S)").isoformat()
            elif vals[i].ctype == xlrd.XL_CELL_EMPTY:
                result[item] = ""
            else:
                print("Excel cell type " + str(vals[i].ctype) + " not supported yet!")
        except Exception as e:
            logger.error("Could not handle column %i: " % (i + 1) + str(e))
            print("Could not handle column %i: " % (i + 1) + str(e))
            return None
    return result


def create_csv_dict(keys, vals):
    result = {}
    for i, item in enumerate(keys):
        try:
            if item == "Veröffentlichungsdatum":
                result[item] = datetime.datetime.strptime(vals[i], "%Y-%m-%d").isoformat().split("T")[0]
            elif item == "Zeitraum Beginn" or (item == "Zeitraum Ende" and vals[i] != ""):
                result[item] = datetime.datetime.strptime(vals[i], "%Y-%m-%d").isoformat().split("T")[0]
            else:
                result[item] = vals[i]
        except Exception as e:
            logger.error("Could not handle column %i: " % (i + 1) + str(e))
            print("Could not handle column %i: " % (i + 1) + str(e))
            return None
    return result


# Obligatory fields must not be empty
def test_on_valid_entries(in_dict):
    try:
        if in_dict['Titel'] == "":
            raise ValueError('"Titel" is empty')
        if in_dict['Beschreibung'] == "":
            raise ValueError('"Beschreibung" is empty')
        if in_dict['Lizenz'] == "":
            raise ValueError('"Lizenz" is empty')
        if in_dict['Veröffentlichungsdatum'] == "":
            raise ValueError('"Veröffentlichungsdatum" is empty')
        if in_dict['Zeitraum Beginn'] == "":
            raise ValueError('"Zeitraum Beginn" is empty')
#        if in_dict['Zeitraum Ende'] == "":
#            raise ValueError('"Zeitraum Ende" is empty')
        if in_dict['Räumliche Ausdehnung'] == "":
            raise ValueError('"Räumliche Ausdehnung" is empty')
        if in_dict['Kategorie'].lower() not in GROUPS_LIST:
            raise ValueError('Group "' + in_dict['Kategorie'].lower() + '" does not exist.')
        if in_dict['Lizenz'] not in VALID_LICENCES.keys():
            raise ValueError('License "' + in_dict['Lizenz'] + '" does not exist.')
        if "-by-" in in_dict['Lizenz'] and in_dict['Text für Namensnennung'] == "":
            raise ValueError('BY-License without name.')
        if "-by-" not in in_dict['Lizenz'] and in_dict['Text für Namensnennung'] != "":
            raise ValueError('BY-License name without BY-License.')
        return True
    except ValueError as e:
        logger.error("Could not handle following value: " + str(e))
        print("Could not handle following value: " + str(e))
        return False


def create_urlname(name):
    vacant = False
    id = 0
    url_wo_arg = 'https://' if HTTPS else 'http://'
    url_wo_arg += HOST + '/api/util/dataset/munge_title_to_name?title='
    if sys.version_info[0] == 2:
        name_out = urllib2.urlopen(urllib2.Request(
          url_wo_arg + urllib2.quote(name))).readline().strip('"')
    elif sys.version_info[0] == 3:  # >=Python3.1
        name_out = urllib.request.urlopen(urllib.request.Request(
          url_wo_arg + urllib.parse.quote(name))).readline().decode('utf-8').strip('"')
    name_with_id = name_out
    while not vacant:
        try:
            result = r_ckan.action.package_show(id=name_with_id)
            id += 1
            name_with_id = name_out + str(id)
        except NotFound:
            vacant = True
        except CKANAPIError:
            # (May occur if skript is not authorized to show a package, but url exists)
            id += 1
            name_with_id = name_out + str(id)
    return name_with_id


def create_extras(in_dict):
    result = []
    result.append({'key': 'issued', 'value': in_dict['Veröffentlichungsdatum']})
    result.append({'key': 'spatial_uri', 'value': in_dict['Räumliche Ausdehnung']})
    result.append({'key': 'licenseAttributionByText', 'value': in_dict['Text für Namensnennung']})
    result.append({'key': 'temporal_start', 'value': in_dict['Zeitraum Beginn']})
    if in_dict['Zeitraum Ende'] != "":
        result.append({'key': 'temporal_end', 'value': in_dict['Zeitraum Ende']})
    return result


# Create 'Schlagwörter'
def create_tags(input_string):
    input_tags = input_string.split(',')
    result = []
    for elem in input_tags:
        result.append({'name': elem.strip()})
    return result


def create_package(in_dict):
    return r_ckan.action.package_create(
             title=in_dict['Titel'],
             name=create_urlname(in_dict['Titel']),
             owner_org=OWNER_ORG,
             notes=in_dict['Beschreibung'],
             license_id=VALID_LICENCES[in_dict['Lizenz']],
             extras=create_extras(in_dict),
             tags=create_tags(in_dict['Schlagwörte']),
             groups=[{'name': in_dict['Kategorie'].lower()}])


def create_resource(d_url, z_url, id):  # Download-, Zugriffs-URL and id of the metadata package.
    # Errors are catched in main routine
    if d_url == "" and z_url == "":
        logger.error("No resource given.")
        raise ValueError('Neither Download-URL nor Zugriffs-URL are specified.')
        logger.error('Neither Download-URL nor Zugriffs-URL are specified.')
    elif d_url != "" and z_url != "":
        raise ValueError('Both Download-URL as well as Zugriffs-URL are specified, '
                         + 'which is not allowed.')
        logger.error('Both Download-URL as well as Zugriffs-URL specified, '
                     + 'which is not allowed.')
    elif d_url != "":
        filetype = d_url.split('.')[-1]  # File extensions, i.e. the part after the last '.'.
        r_ckan.action.resource_create(
          package_id=id,
          upload=open(os.path.join(PATH, d_url), 'rb'),
          name=d_url[:-(len(filetype) + 1)],  # Resourcename from Download-URL without extension
          format=filetype.upper())
    else:  # Zugriffs-URL != None
        r_ckan.action.resource_create(
          package_id=id,
          url=z_url,
          description=z_url.split('/')[-1],
          name=z_url.split('/')[-1],
          format=z_url.split('.')[-1].upper())
    return True


###########################
#  Logger initialisation  #
###########################

logger = logging.getLogger('CKAN')
logger.setLevel(logging.INFO)
fh = logging.FileHandler(os.path.join(PATH, LOGFILE_NAME))
fh.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

#################################
#  Accessing Excel or csv file  #
#################################

fileformat = ""
try:
    if FILENAME.split('.')[-1].upper() in ["XLS", "XLSX"]:
        wb = xlrd.open_workbook(os.path.join(RESOURCE_PATH, FILENAME))
        fileformat = "Excel"
    elif FILENAME.split('.')[-1].upper() == "CSV":
        rows = []
        with open(os.path.join(RESOURCE_PATH, FILENAME)) as csvfilehandler:
            csvreader = csv.reader(csvfilehandler, delimiter=CSV_FILE_DELIMITER)
            for row in csvreader:
                rows.append(row)
        fileformat = "CSV"
        if len(row[0]) == 1:  # More than just one column is expected
            raise ValueError("Wrong CSV file delimiter.")
    else:
        raise ValueError("File format not recognised of %s!" % os.path.join(RESOURCE_PATH, FILENAME))
except (IOError, FileNotFoundError) as e:
    logger.error("Could not find Metadata file at " + os.path.join(RESOURCE_PATH, FILENAME))
    print("Could not find Metadata file at " + os.path.join(RESOURCE_PATH, FILENAME))
    sys.exit()
except ValueError as e:
    logger.error(str(e))
    print(str(e))
    sys.exit()

##########################
#    Initialise keys     #
##########################

if fileformat == "Excel":
    sheet = wb.sheets()[0]
    datemode = wb.datemode
    keys = sheet.row_values(0)
    rowcount = sheet.nrows
else:  # fileformat == "CSV"
    keys = rows[0]
    rowcount = len(rows)

check_keys(keys)

##########################
#     Main routine       #
##########################

error_count = 0
for row_num in range(1, rowcount):  # row 0 contains the keys
    spreadsheet_row_num = row_num + 1  # first row is '1', not '0'
    try:  # Create metadata
        success_meta = False
        if fileformat == "CSV":
            row_dict = create_csv_dict(keys, rows[row_num])
        else:
            row_dict = create_xls_dict(keys, sheet.row(row_num), datemode)

        if row_dict is None:
            raise ValueError('')
        if not test_on_valid_entries(row_dict):
            raise ValueError('')
        package_id = create_package(row_dict)['id']
        success_meta = True
    except Exception as e:
        logger.error("Error occured while processing row "
                     + str(spreadsheet_row_num) + ", package was not created!\n" + str(e))
        print("Error occured while processing row "
              + str(spreadsheet_row_num) + ", package was not created!\n" + str(e))
        error_count += 1
    if success_meta:
        success_res = False
        try:  # Create resource
            success_res = create_resource(
                            row_dict['Download-URL'],
                            row_dict['Zugriffs-URL'], package_id)
        except Exception as e:
            print("Error occured while processing resource in row "
                  + str(spreadsheet_row_num) + ", no resource added!\n" + str(e))
            logger.error("Error occured while processing resource in row "
                         + str(spreadsheet_row_num) + ", no resource added!\n" + str(e))
            error_count += 1
        if success_res:
            logger.info("Successfully added metadata "
                        + "and resource of row %i." % spreadsheet_row_num)
if error_count:
    print("%i error(s) occurred. See logfile for more details." % error_count)
