# This version of the script is for submissions that came in and needed modification.

# import all needed modules
import os
import arcpy
import zipfile
import shutil
import datetime
import sqlite3
import winsound

# set ArcGIS environments
arcpy.env.outputMFlag = "Disabled"
arcpy.env.outputZFlag = "Disabled"

# set directories on local drive
geo_area = r'\\batch4.ditd.census.gov\mtdata003_geoarea\BAS'
geoShape = r'\\batch4.ditd.census.gov\mtdata003_geo_shpgen\mtps_mtdb'

# some of these are for sure old and not needed anymore. ask Nick which can just get deleted?
swim_dir = os.path.join(geo_area, 'Digital_BAS_2016\Local_Submission')
bas_dir = os.path.join(geo_area, 'Digital_BAS_2016\processing')
blisrds = os.path.join(geo_area, 'BLISRDS_STAGE')
bench_dir = os.path.join(geoShape, 'bas16_2015')
bench_base = 'bas16_2015_'
bas_yy_county_merge = os.path.join(geo_area, 'ABEUS\bas16countymerge.shp')  # change before production
log_db = os.path.join(bas_dir, 'basSetup.db')
mxd_template = os.path.join(geo_area, 'Digital_BAS_2016\Templates\preprocess_template3.mxd')


# generic dictionaries for GDBs
ccd_list = ('01', '02', '04', '06', '08', '10', '12', '13', '15', '16', '21',
            '30', '32', '35', '40', '41', '45', '48', '49', '53', '56')
change_types = {'incplace': '_changes_incplace.shp',
                'cousub': '_changes_cousub.shp',
                'concity': '_changes_concity.shp',
                'aiannh': '_changes_aiannh.shp',
                'ln': '_ln_changes.shp',
                'hydroa': '_hydroa_changes.shp',
                'plndk': '_plndk_changes.shp',
                'alndk': '_alndk_changes.shp',
                'county': '_changes_county.shp'}

change_fields_id = {'incplace': 'PLACEFP',
                    'cousub': 'COUSUBFP',
                    'concity': 'CONCITYFP',
                    'county': 'COUNTYFP',
                    'aiannh': 'AIANNHCE',
                    'ln': 'TLID',
                    'hydroa': 'HYDROID',
                    'plndk': 'POINTID',
                    'alndk': 'AREAID'}

change_fields_req = {'incplace': ['STATEFP',
                                  'PLACEFP',
                                  'NAME',
                                  'NAMELSAD',
                                  'CHNG_TYPE',
                                  'EFF_DATE',
                                  'DOCU',
                                  'AREA',
                                  'RELATE'],
                     'county': ['STATEFP',
                                'COUNTYFP',
                                'NAME',
                                'NAMELSAD',
                                'CHNG_TYPE',
                                'EFF_DATE',
                                'DOCU',
                                'AREA',
                                'RELATE'],
                     'cousub': ['STATEFP',
                                'COUNTYFP',
                                'COUSUBFP',
                                'NAME',
                                'NAMELSAD',
                                'CHNG_TYPE',
                                'EFF_DATE',
                                'DOCU',
                                'AREA',
                                'RELATE'],
                     'concity': ['STATEFP',
                                 'CONCITYFP',
                                 'NAME',
                                 'NAMELSAD',
                                 'CHNG_TYPE',
                                 'EFF_DATE',
                                 'DOCU',
                                 'AREA',
                                 'RELATE'],
                     'aiannh': ['AIANNHCE',
                                'NAME',
                                'NAMELSAD',
                                'CHNG_TYPE',
                                'EFF_DATE',
                                'DOCU',
                                'AREA',
                                'RELATE'],
                     'ln': ['TLID',
                            'FULLNAME',
                            'CHNG_TYPE',
                            'MTFCC'],
                     'hydroa': ['HYDROID',
                                'FULLNAME',
                                'CHNG_TYPE',
                                'MTFCC',
                                'RELATE'],
                     'plndk': ['POINTID',
                               'FULLNAME',
                               'CHNG_TYPE',
                               'MTFCC'],
                     'alndk': ['AREAID',
                               'FULLNAME',
                               'CHNG_TYPE',
                               'MTFCC',
                               'RELATE']}

table_criteria = {'STATEFP': ["TEXT", '2'],
                  'COUNTYFP': ["TEXT", '3'],
                  'COUNTYNS': ["TEXT", '8'],
                  'NAMELSAD': ["TEXT", '100'],
                  'LSAD': ["TEXT", '2'],
                  'FUNCSTAT': ["TEXT", '1'],
                  'CLASSFP': ["TEXT", '2'],
                  'CHNG_TYPE': ["TEXT", '2'],
                  'EFF_DATE': ["DATE", '8'],
                  'AUTHTYPE': ["TEXT", '1'],
                  'DOCU': ["TEXT", '120'],
                  'FORM_ID': ["TEXT", '4'],
                  'AREA': ["DOUBLE", '10'],
                  'RELATE': ["TEXT", '120'],
                  'JUSTIFY': ["TEXT", '150'],
                  'NAME': ["TEXT", '100'],
                  'VINTAGE': ["TEXT", '2'],
                  'PLACEFP': ["TEXT", '5'],
                  'COUSUBFP': ["TEXT", '5'],
                  'CONCITYFP': ["TEXT", '5'],
                  'AIANNHCE': ["TEXT", '4']}


# this affects later bits of code but need to make sure i can make it a function
try:  # fix this up later?
    conn = sqlite3.connect(log_db, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.execute("CREATE TABLE IF NOT EXISTS ENTITIES (BASID TEXT, FILENAME TEXT, FOLDER TEXT, STATE TEXT,"
                 "SUBTYPE TEXT,COUNTIES TEXT,ERRORS TEXT,TIMESTAMP NUMERIC)")
    conn.execute("CREATE TABLE IF NOT EXISTS SHAPEFILES (BASID TEXT, FILENAME TEXT, SHP TEXT, CHANGETYPE TEXT,"
                 "GDBFC TEXT, FLDERRORS TEXT, VALUEERRORS TEXT, PRJ TEXT)")
except:  # fix this up later?
    pass


# plays a notification sound, unsure if actually works
def notify():
    try:
        winsound.PlaySound("SystemQuestion", winsound.SND_ALIAS)
    except:
        pass


# this is generally only used once per BAS cycle
def bench_county_merge(bench_dir, bench_base, bas_yy_county_merge):  # use to create merged file of counties 'BAS16countyMerge'
    merge_list2 = list(os.path.join(bench_dir, x, bench_base, 'county_', x, '.shp')
                       for x in os.listdir(bench_dir)
                       if len(x) == 2)
    arcpy.Merge_management(merge_list2, bas_yy_county_merge)


# creates a log file for processor to review
def log_it(connection, bas_id, filename, folder, state, subtype, counties, errors, timestamp, shp_dict):
    # creates and opens text file for logging errors
    f = open(os.path.join(folder, 'log.txt'), 'w')
    # inserts BAS ID at the top of the txt file
    f.write(bas_id + '\n')

    # prints list of errors if there are any to text file
    if errors:
        f.write('errors: \n')
        for x in errors:  # loops through the list of errors and inserts them on a new line
            f.write('    ' + str(x) + '\n')

    # writes the submission type to the text file
    f.write('Submission Type:\n    ' + str(subtype) + '\n')

    # any intersecting counties are written to file here and if there aren't any, puts none
    if counties:
        f.write('Affected counties:\n\n')
        f.write(','.join(counties))
        f.write('\n\n')
    else:
        f.write('Affected counties:\n    None\n')

    try:  # fix this up later?
        connection.execute("insert into ENTITIES values(?,?,?,?,?,?,?,?);", (bas_id, filename, folder, state, subtype,
                                                                             str(counties), str(errors), timestamp))
    except:  # fix this up later?
        pass

    # checks attributes based on type of file and outputs lists of missing values
    if shp_dict:
        f.write('==Shapefile Summary==============================\n')
        for shp, values in shp_dict.iteritems():
            connection.execute("insert into SHAPEFILES values(?,?,?,?,?,?,?,?);", (bas_id,
                                                                                   filename,
                                                                                   shp,
                                                                                   str(values['changetype']),
                                                                                   str(values['GDBFC']),
                                                                                   str(values['fldErrors']),
                                                                                   str(values['valueErrors']),
                                                                                   str(values['prj'])))
            f.write('Shapefile:\n    ' + shp + '\n')  # prints path of file that was processed (print just the name?)
            f.write('Change Type:\n    ' + str(values['changetype']) + '\n')  # type of geography changed
            if values['fldErrors']:  # checks FOR required fields in shapefile
                f.write('Expected field(s) missing:\n')
                for v in values['fldErrors']:
                    f.write('    ' + str(v) + '\n')
            if values['valueErrors']:  # checks for missing/inconsistent data IN required fields
                f.write('values missing from key fields:\n')
                if values['changetype'] in ['ln', 'hydroa', 'plndk', 'alndk']:
                    f.write('* FEAT_ID is a stand-in for TLID, AREAID, POINTID, or HYDROID depending on layer\n')
                    f.write('    FID | FULLNAME | CHNG_TYPE | RELATE | MTFCC | FEAT_ID* | PROBLEM \n')
                else:
                    f.write('    FID | NAME | CHNG_TYPE | EFF_DATE | DOCU | AREA | RELATE | PROBLEM \n')
                for v in values['valueErrors']:
                    if type(v) == type(('',)):
                        f.write('    ' + ' | '.join(list(str(x) for x in v)) + '\n')
                    else:
                        f.write('    ' + str(v) + '\n')

            if values['prj'] is False:  # checks that shp has a projection
                f.write('!Missing .PRJ file!\n')

            if values['GDBFC']:
                f.write('layer name in GDB:\n    '+values['GDBFC']+'\n')

            f.write('=================================================\n')
    connection.commit()
    f.close()


def get_counties(change_list, usa_county_fc):
    out_list = []
    tmp = arcpy.MakeFeatureLayer_management(usa_county_fc, "in_memory\\counties")
    for fc in change_list:
        arcpy.SelectLayerByLocation_management(tmp, "WITHIN_A_DISTANCE", fc, '1 FEET', "ADD_TO_SELECTION")
    cur = arcpy.SearchCursor(tmp)
    for row in cur:
        out_list.append(row.STATEFP + row.COUNTYFP)
    arcpy.Delete_management(tmp)
    del cur
    return out_list


def import_support(gdb, county_list, folder, state, srcRoot=bench_dir, srcBase = bench_base):
    if state == '02':  # Alaska
        arcpy.CreateFeatureDataset_management(
            gdb,
            "benchmark",
            "PROJCS['NAD_1983_Alaska_Albers',"
            "GEOGCS['GCS_North_American_1983',"
            "DATUM['D_North_American_1983', "
            "SPHEROID['GRS_1980',6378137.0,298.257222101]],"
            "PRIMEM['Greenwich', 0.0],"
            "UNIT['Degree', 0.0174532925199433]], "
            "PROJECTION['Albers'], "
            "PARAMETER['False_Easting',0.0],"
            "PARAMETER['False_Northing',0.0], "
            "PARAMETER['Central_Meridian',-154.0],"
            "PARAMETER['Standard_Parallel_1',55.0], "
            "PARAMETER['Standard_Parallel_2',65.0],"
            "PARAMETER['Latitude_Of_Origin',50.0],"
            "UNIT['Meter',1.0]];-13752200 -8948200 10000;-100000 10000;-100000 10000;0.001;0.001;0.001;IsHighPrecision"
        )
    elif state == '15':  # Hawaii
        arcpy.CreateFeatureDataset_management(
            gdb,
            "benchmark",
            "PROJCS['Hawaii_Albers_Equal_Area_Conic', "
            "GEOGCS['GCS_North_American_1983',"
            "DATUM['D_North_American_1983', "
            "SPHEROID['GRS_1980',6378137.0,298.257222101]],"
            "PRIMEM['Greenwich',0.0], "
            "UNIT['Degree',0.0174532925199433]], "
            "PROJECTION['Albers'], "
            "PARAMETER['False_Easting',0.0],"
            "PARAMETER['False_Northing',0.0], "
            "PARAMETER['Central_Meridian',-157.0],"
            "PARAMETER['Standard_Parallel_1',8.0], "
            "PARAMETER['Standard_Parallel_2',18.0],"
            "PARAMETER['Latitude_Of_Origin',13.0],"
            "UNIT['Meter',1.0]];-22487400 -7108900 10000;-100000 10000;-100000 10000;0.001;0.001;0.001;IsHighPrecision"
        )
    else:  # contiguous USA 48
        arcpy.CreateFeatureDataset_management(
            gdb,
            "benchmark",
            "PROJCS['USA_Contiguous_Albers_Equal_Area_Conic_USGS_version',"
            "GEOGCS['GCS_North_American_1983', "
            "DATUM['D_North_American_1983',"
            "SPHEROID['GRS_1980',6378137.0,298.257222101]], "
            "PRIMEM['Greenwich',0.0],"
            "UNIT['Degree',0.0174532925199433]], "
            "PROJECTION['Albers'],"
            "PARAMETER['False_Easting',0.0], "
            "PARAMETER['False_Northing',0.0],"
            "PARAMETER['Central_Meridian',-96.0], "
            "PARAMETER['Standard_Parallel_1',29.5],"
            "PARAMETER['Standard_Parallel_2',45.5], "
            "PARAMETER['Latitude_Of_Origin',23.0],"
            "UNIT['Meter',1.0]];-16901100 -6972200 10000;-100000 10000;-100000 10000;0.001;0.001;0.001;IsHighPrecision"
        )
    support_fd = os.path.join(gdb, 'benchmark')

    if state in ccd_list:
        cou_subtype = 'ccd'
    else:
        cou_subtype = 'mcd'
    merge_lyr_list = ['aial', 'arealm', 'cdp', 'concity', 'county', 'edges', 'offset', 'place', 'pointlm', 'water']

    for county in county_list:
        shutil.copytree(os.path.join(bench_dir, county), os.path.join(folder, county))

    arcpy.Merge_management(list(os.path.join(folder, x, srcBase, cou_subtype, '_'+x+'.shp') for x in county_list),
                           support_fd + '\\bas_cousub')
    for lyr in merge_lyr_list:
        arcpy.Merge_management(list(folder+'\\'+x+'\\'+srcBase+lyr+'_'+x+'.shp' for x in county_list), support_fd + '\\bas_' + lyr)


def lisrds(counties_list):
    for cou in counties_list:
        f_file = os.path.join(blisrds, cou, '.txt')
        f = open(f_file)
        f.close()


def whichZip(srcdir, basid):
    results = []
    for f in os.listdir(srcdir):
        if f[-4:].lower() == '.zip':
            results.append(f)
    if len(results) == 0:  # there is no ZIP file here
        print 'Could not find any zipfiles'
        return None
    if len(results) == 1:  # there is only one zipfile
        return results[0]
    question = """=========================================================================
More than one ZIP file was found for %s.
Please select one from the list below.
Type its number and press enter.
=========================================================================
"""%basid
    for name in results:
        question += str(results.index(name)) + ': ' + name + '\n'
    while 1:
        notify()
        x = raw_input(question)
        if not x:
            return None
        elif x.isdigit() and int(x) < len(results):
            print '*'*34 + '\n*   Running BASID: '+ basid + '   *' + '\n'+'*'*34
            return results[int(x)]
        else:
            print "The value {0} could not be used, try again please.".format(x)


# generate SWECS path based on BASID and file name
def zipPath(basid):
    st = basid[1:3]
    if basid[0] == '1':  # incplace
        swecsgeocode = basid[1:3]+basid[-5:]
    elif basid[0] == '2':  # county
        swecsgeocode = basid[1:6]
    elif basid[0] == '3':  # cousub
        swecsgeocode = basid[1:]
    elif basid[0] == '4':  # aial
        swecsgeocode = basid[3:7]
    elif basid[0] == '0':  # concity
        swecsgeocode = basid[1:3]+basid[-5:]
    return os.path.join(swim_dir, st, basid)


# extract contents of zip file
def extractZip(source, output):
    with zipfile.ZipFile(source, 'r') as zf:
        zf.extractall(output)


# figure out MTPS vs digital
def submissionType(path):
    for x,y,z in os.walk(path):
        for f in z:
            if f[-8:].upper() == 'FORM.DBF':
                return 'MTPS'
            elif f[-5:].upper() == '.GUPS':
                return 'GUPS'
    return 'DIGITAL'


# get form.dbf
def getFormDBF(path):
    for x,y,z in os.walk(path):
        for f in z:
            if f[-8:] == 'FORM.DBF':
                return x + '\\' + f
    results = []
    for x,y,z in os.walk(path):
        for f in z:
            if 'form' in f.lower():
                results.append(x+'\\'+f)
    if len(results):
        return results
    return None


# get list of shapefiles
def getSHPs(path):
    results=[]
    for x,y,z in os.walk(path):
        for f in z:
            if f[-4:].lower() == '.shp':
                results.append((x,f))
    return results


# subset shapefile list for changes SHPs
def chngSHPs(shpList):
    results = []
    for path,fn in shpList:
        x = path + '\\' + fn
        if 'change' in fn.lower():
            results.append(x)
    return results


# determine type of changes shapefile
def chngType(chngSHP):  # input full path to shapefile.
    # returns a change type, or 'missmatch' if name of file does not match key field,
    # or 'nomatch' if it could not match up either.
    # the number returned is confidence level, do not process 0s, 2 is full confidence, 1 is good enough to try.
    fldlst = []
    for field in arcpy.ListFields(chngSHP):
        fldlst.append(field.name)
    # nfirst try checking just by file name, exact match only
    for key, value in change_types.iteritems():
        if chngSHP[len(value)*(-1):].lower()==value:
            chtype = key
            if change_fields_id[chtype] in fldlst:
                return chtype
            else:
                return 'mismatch'
    for key, value in change_fields_id.iteritems():
        if value in fldlst and not value=='COUNTYFP':
            return key
#    else:
#        if value == 'COUNTYFP':
#            return 'county'
    return 'nomatch'


# check for .prj file for each changes shp. do before importing to GDB.
def prjChk(chngSHP):#input full path to shapefile.
    return os.path.exists(chngSHP[:-3]+'prj')


# attempt to import changes layer into the GDB\FD
# rename at the same time.
def integrateChng(chngSHP, FD, basid, chngtype):
    # input full path to shapefile and full path to Feature Dataset
    # the FD is already projected, so the files will be forced into projection on import.
    # if the file projection is not known(no .prj info) then the import will most likely place them in the wrong spot.
    outputFC = 'bas16_' + basid + '_changes_' + chngtype
    arcpy.FeatureClassToFeatureClass_conversion(chngSHP, FD, outputFC)


# MTPS only, for each changes Feature Class import the info from the FORM DBF:
def formIDupdate(formDBF, FC):  # input full path to formDBF and to a changes FC.
    templyr = arcpy.MakeFeatureLayer_management(FC, "in_memory\\templyr")
    tempform = arcpy.MakeTableView_management(formDBF,"in_memory\\tempform")
    lyrwhere = '''"CHNG_TYPE" IN ('A', 'D')'''
    curlyr = arcpy.UpdateCursor(templyr,lyrwhere)
    for row in curlyr:
        formid = row.FORM_ID
        formwhere = '''"ID" = '%s\''''% formid
        formrow = arcpy.SearchCursor(tempform,formwhere).next()
        row.setValue("EFF_DATE", formrow.getValue("DATE"))
        row.setValue("AUTHTYPE", formrow.getValue("AUTHTYPE"))
        row.setValue("DOCU", formrow.getValue("AUTHNUM"))
        row.setValue("AREA", float(formrow.getValue("AREA")))#added per request from Shawn Smith.
        curlyr.updateRow(row)
    del curlyr
    arcpy.Delete_management(tempform)
    arcpy.Delete_management(templyr)


# check a change layer to make sure it has the required fields
# import the changes layers into the GDB\FD before doing this, then run on the Feature class rather than the shapefiles.
def fldChk(chngFC, chngType):
    fields = {}
    for f in arcpy.ListFields(chngFC):
        fields[f.name.upper()] = f.type
    problems = []
    for n in change_fields_req[chngType]:
        try:
            if not fields[n] == 'String' and n not in ['EFF_DATE', 'AREA', 'POINTID', 'AREAID', 'HYDROID', 'TLID']:
                problems.append('Field "'+n+'" is not String type.')
        except:
            problems.append('Field "'+n+'" was missing, you will need to populate this field.')
            b = table_criteria[n]
            ftype = b[0]
            flength = b[1]
            arcpy.AddField_management(chngFC, n, ftype, field_length= flength)

    return problems


# check that appropriate values reside in name, chng_type, eff_date, docu, area, & relate fields
# run this after the fldChk, run it on the SHP not the FC.
def valChk(chngFC, georgia=False):
    output = []
    for row in arcpy.SearchCursor(chngFC):
        problem = ''
        FID = row.FID
        NAME= row.NAME.strip()
        CHNG_TYPE = row.CHNG_TYPE
        EFF_DATE = str(row.EFF_DATE).strip()
        DOCU = row.DOCU.strip()
        AREA = row.AREA
        RELATE = row.RELATE
        if not NAME:
            problem += 'no name, '
        if not CHNG_TYPE.upper() in ['A', 'B', 'C', 'D', 'E', 'F', 'X']:
            problem += 'invalid change type, '
        if CHNG_TYPE.upper() in ['A', 'D', 'E', 'X'] and not EFF_DATE:
            problem += 'missing effective date, '
        if not georgia:
            if CHNG_TYPE.upper() in ['A', 'D', 'E', 'X'] and not DOCU:
                problem += 'missing legal documentation, '
        else:  # it is georgia
            if CHNG_TYPE.upper() in ['A', 'D', 'E', 'X'] and not AREA:
                problem += 'Georgia legal change missing area calculation, '
        if CHNG_TYPE.upper() in ['B', 'C', 'F'] and not RELATE.upper() in ['IN', 'OUT']:
            problem += 'missing valid RELATE info, '
        if problem:
            output.append((FID, NAME, CHNG_TYPE, EFF_DATE, DOCU, AREA, RELATE, problem[:-2]))
    return output


def valChk2(chngFC, CT):
    output = []
    for row in arcpy.SearchCursor(chngFC):
        problem = ''
        FID = row.FID
        FULLNAME = row.FULLNAME.strip()
        CHNG_TYPE = row.CHNG_TYPE
        MTFCC = row.MTFCC.strip()
        if CT == 'ln':
            FEAT_ID = row.TLID
            RELATE = ''
            if not CHNG_TYPE.upper() in ['AL', 'DL', 'CA', 'SL']:
                problem += 'invalid change type, '
            if CHNG_TYPE.upper() == 'AL' and not MTFCC:
                problem += 'AL change missing MTFCC code, '
            if CHNG_TYPE.upper() in ['DL', 'CA'] and not FEAT_ID:
                problem += 'DL or CA change missing TLID value, '
            if CHNG_TYPE.upper() == 'CA' and not (FULLNAME or MTFCC):
                problem += 'CA change type requires either FULLNAME or MTFCC, '
        elif CT == 'hydroa':
            FEAT_ID = row.HYDROID.strip()
            RELATE = row.RELATE
            if not CHNG_TYPE.upper() in ['B', 'D', 'G', 'E']:
                problem += 'invalid change type, '
            if CHNG_TYPE.upper() in ['B', 'D', 'G'] and not FEAT_ID:
                problem += 'B, D, or G change missing HYDROID value, '
            if CHNG_TYPE.upper() in ['B', 'G', 'E'] and not FULLNAME:
                problem += 'B, G, or E change missing FULLNAME value, '
            if CHNG_TYPE.upper() == 'B' and not RELATE.upper() in ['IN', 'OUT']:
                problem += 'missing valid RELATE info, '
            if CHNG_TYPE.upper() == 'E' and not MTFCC:
                problem += 'E change missing MTFCC value, '
        elif CT == 'plndk':
            FEAT_ID = row.POINTID.strip()
            RELATE = ''
            if not CHNG_TYPE.upper() in ['X', 'G', 'E']:
                problem += 'invalid change type, '
            if CHNG_TYPE.upper() in ['E', 'G'] and not FULLNAME:
                problem += 'E or G change missing FULLNAME value, '
            if CHNG_TYPE.upper() in ['D', 'G'] and not FEAT_ID:
                problem += 'D or G change missing POINTID value, '
            if CHNG_TYPE.upper() == 'E' and not MTFCC:
                problem += 'E change missing MTFCC value, '
        elif CT == 'alndk':
            FEAT_ID = row.AREAID.strip()
            RELATE = row.RELATE
            if not CHNG_TYPE.upper() in ['B', 'D', 'G', 'E']:
                problem += 'invalid change type, '
            if CHNG_TYPE.upper() in ['B', 'D', 'G'] and not FEAT_ID:
                problem += 'B, D, or G change missing AREAID value, '
            if CHNG_TYPE.upper() in ['B', 'G', 'E'] and not FULLNAME:
                problem += 'B, G, or E change missing FULLNAME value, '
            if CHNG_TYPE.upper() == 'B' and not RELATE.upper() in ['IN', 'OUT']:
                problem += 'missing valid RELATE info, '
            if CHNG_TYPE.upper() == 'E' and not MTFCC:
                problem += 'E change missing MTFCC value, '
        if problem:
            output.append((FID, FULLNAME, CHNG_TYPE, RELATE, MTFCC, FEAT_ID, problem[:-2]))
    return output


def DescShp(shp):  # prints list of filed names and their types.
    print 'NAME        TYPE'
    print '===================='
    for f in arcpy.ListFields(shp):
        print f.name + '  ' + ' '*(10-len(f.name)) + f.type
    print '===================='


def PreviewAttr(shp, limit=10):  # prints a few rows from attribute table.
    fields = list(f.name for f in arcpy.ListFields(shp))
    try:
        fields.pop(fields.index('Shape'))
    except:
        pass
    print ' | '.join(fields)
    cur = arcpy.SearchCursor(shp)
    for x in range(limit):
        row = cur.next()
        if row:
            print ' | '.join(list(str(row.getValue(f)) for f in fields))
    del cur


def cantFindChanges(shptupples):  # if script cant find changes file then ask user to find them.
    shplist = list(x + '\\' + y for x, y in shptupples)
    question = """=========================================================================
The following shapefiles could not be identified.
Which, if any, are changes files?
Input a list of the numbers for each shapefile that is a changes file,
do not enter anything if you are unsure.
To see a list of Attribute fields for a given shapefile
enter 'desc #' where the number corresponds to the shapefile of interest.
=========================================================================
"""
    for name in shplist:
        question += str(shplist.index(name)) + ': ' + name + '\n'
    while 1:
        notify()
        x = raw_input(question)
        if not x:
            return None
        elif x[:5] == 'desc ':
            try:
                descx = int(x[5:])
                if descx <= len(shplist)-1:
                    print 'Describing {0}, {1}:'.format(str(descx), shplist[descx])
                    DescShp(shplist[descx])
                else:
                    print 'Could not describe item "{0}". It is out of range.'.format(x[5:])
                continue
            except:
                print 'Could not describe item "{0}". It is out of range.'.format(x[5:])
                continue
        else:
            try:
                listx = list(int(y) for y in x.split(','))
            except:
                print 'Could not parse list "{0}". Please try again.'.format(x)
                continue
        outlist = []
        try:
            for z in listx:
                outlist.append(shplist[z])
        except:
            print 'Could not use list. Value "{0}" is out of range.'.format(z)
            continue
        else:
            return outlist


def cantFindChangeType(shppath):  # if script cant figure out what type of change it is, ask user to decide
    typelist = ['concity', 'incplace', 'county', 'cousub', 'aiannh']
    print "====================\nCannot figure out what type of entities this changes shapefile is for:"
    print shppath
    print '===================='
    DescShp(shppath)
    question = """What kind of change is it?
0 concity
1 incplace
2 county
3 cousub
4 aiannh
Enter the correct number from the options above.
Enter 'desc' to view a few rows from the attribute table.
Enter nothing to skip this changes shapefile.
"""
    while 1:
        notify()
        x = raw_input(question)
        if not x:
            return None
        elif x == 'desc':
            print "==============================================="
            PreviewAttr(shppath)
            print "==============================================="
            continue
        else:
            try:
                return typelist[int(x)]
            except:
                print '"' + x + '" is not a valid option, try again.'
                continue


def runit(basid, supervised=True):
    print '*'*34 + '\n*   Running BASID: ' + basid + '   *' + '\n'+'*'*34
    state = basid[1:3]
    stfolder = bas_dir+'\\'+state
    if not os.path.exists(stfolder):
        os.mkdir(stfolder)
    folder = stfolder+'\\'+basid
    zp = zipPath(basid)
    filename = whichZip(zp,basid)
    if not filename:
        print "No zip file encountered for " +basid
        return
    fullzipsrc = zp + '\\' + filename
    errors = []
    shp_dict = {}
    subType = None
    counties = None
    if state == '13':
        georgia = True
    else:
        georgia = False
    try:
        os.mkdir(folder)
    except Exception, e:
        print 'Could not make project directory.'
        print e
    try:
        extractZip(fullzipsrc, folder)
    except Exception, e:
        errors.append('Could not extract ZIP file.')
        log_it(conn, basid, filename, folder, state, subType, counties, errors, datetime.datetime.now(), shp_dict)
    try:
        subType = submissionType(folder)
        shplist = getSHPs(folder)
        if not shplist:
            errors.append('No shapefiles found') #log_it
            log_it(conn, basid, filename, folder, state, subType, counties, errors, datetime.datetime.now(), shp_dict)
            return
        for path, fn in shplist:
            shp_dict[path+'\\'+fn] = {'changetype':None, 'GDBFC':None, 'fldErrors':None, 'valueErrors':None, 'prj':None}
        changeFiles = chngSHPs(shplist)
        if not changeFiles:  #ask the user
            changeFiles = cantFindChanges(shplist)
        if not changeFiles:  #still no changes shapefile, time to give up.
            errors.append('No changes identified') #log_it
            log_it(conn, basid, filename, folder, state, subType, counties, errors, datetime.datetime.now(), shp_dict)
            return

        for CF in changeFiles:
            CT = chngType(CF)
            if CT[:7] in ['mismatc', 'nomatch']:
                print CT
                ct = cantFindChangeType(CF)
                if ct:
                    CT = ct
            shp_dict[CF]['changetype'] = CT
        if subType == 'MTPS':
            formid = getFormDBF(folder)
            for CF in changeFiles:
                if shp_dict[CF]['changetype'] in ['incplace', 'cousub', 'concity', 'aiannh']:
                    formIDupdate(formid, CF)
    
        arcpy.CreateFileGDB_management(folder, "DB"+basid)
        GDB = folder + '\\' + "DB" + basid + '.gdb'
        if state == '02':  # Alaska
            arcpy.CreateFeatureDataset_management(
                GDB, "submission", "PROJCS['NAD_1983_Alaska_Albers', GEOGCS['GCS_North_American_1983',"
                                   "DATUM['D_North_American_1983', SPHEROID['GRS_1980',6378137.0,298.257222101]],"
                                   "PRIMEM['Greenwich',0.0], UNIT['Degree',0.0174532925199433]],"
                                   "PROJECTION['Albers'], PARAMETER['False_Easting',0.0],"
                                   "PARAMETER['False_Northing',0.0], PARAMETER['Central_Meridian',-154.0],"
                                   "PARAMETER['Standard_Parallel_1', 55.0], PARAMETER['Standard_Parallel_2',65.0],"
                                   "PARAMETER['Latitude_Of_Origin', 50.0], UNIT['Meter',1.0]];"
                                   "-13752200 -8948200 10000;-100000 10000;-100000 10000;0.001;0.001;0.001;IsHighPrecision")
        elif state == '15':  # Hawaii
            arcpy.CreateFeatureDataset_management(
                GDB, "submission", "PROJCS['Hawaii_Albers_Equal_Area_Conic', GEOGCS['GCS_North_American_1983',"
                                   "DATUM['D_North_American_1983', SPHEROID['GRS_1980',6378137.0,298.257222101]],"
                                   "PRIMEM['Greenwich',0.0], UNIT['Degree',0.0174532925199433]], PROJECTION['Albers'],"
                                   "PARAMETER['False_Easting',0.0], PARAMETER['False_Northing',0.0], "
                                   "PARAMETER['Central_Meridian',-157.0], PARAMETER['Standard_Parallel_1',8.0],"
                                   "PARAMETER['Standard_Parallel_2',18.0], PARAMETER['Latitude_Of_Origin',13.0],"
                                   "UNIT['Meter',1.0]];-22487400 -7108900 10000;-100000 10000;-100000 10000;0.001;0.001;0.001;IsHighPrecision")
        else:    # contiguous USA 48
            arcpy.CreateFeatureDataset_management(
                GDB, "submission", "PROJCS['USA_Contiguous_Albers_Equal_Area_Conic_USGS_version',"
                                   "GEOGCS['GCS_North_American_1983', DATUM['D_North_American_1983',"
                                   "SPHEROID['GRS_1980',6378137.0,298.257222101]], PRIMEM['Greenwich',0.0],"
                                   "UNIT['Degree',0.0174532925199433]], PROJECTION['Albers'], "
                                   "PARAMETER['False_Easting',0.0], PARAMETER['False_Northing',0.0],"
                                   "PARAMETER['Central_Meridian',-96.0], PARAMETER['Standard_Parallel_1',29.5],"
                                   "PARAMETER['Standard_Parallel_2',45.5], PARAMETER['Latitude_Of_Origin',23.0],"
                                   "UNIT['Meter',1.0]];-16901100 -6972200 10000;-100000 10000;-100000 10000;0.001;0.001;0.001;IsHighPrecision")
        FD = GDB + '\\submission'
        for CF in changeFiles:
            CT = shp_dict[CF]['changetype']
            if CT in change_types.keys():
                shp_dict[CF]['fldErrors'] = fldErrors = fldChk(CF,CT)

                arcpy.AddField_management(CF, "PROCESS", "TEXT", field_length=1)
                arcpy.AddField_management(CF, "P_COMMENTS", "TEXT", field_length=200)
                arcpy.AddField_management(CF, "VERIFY", "TEXT", field_length=1)
                arcpy.AddField_management(CF, "V_COMMENTS", "TEXT", field_length=200)
                arcpy.AddField_management(CF, "DIGITIZE", "TEXT", field_length=1)
                arcpy.AddField_management(CF, "D_COMMENTS", "TEXT", field_length=200)
                arcpy.AddField_management(CF, "QC", "TEXT", field_length=1)
                arcpy.AddField_management(CF, "Q_COMMENTS", "TEXT", field_length=200)

                try:
                    if CT in ['ln', 'hydroa', 'plndk', 'alndk']:
                        shp_dict[CF]['valueErrors'] = valueErrors = valChk2(CF, CT)
                    else:
                        shp_dict[CF]['valueErrors'] = valueErrors = valChk(CF, georgia)
                except:
                    shp_dict[CF]['valueErrors'] = valueErrors = ['values could not be checked; perhaps a key field is missing.']
                shp_dict[CF]['prj'] = prj = prjChk(CF)
                if not prj:
                    errors.append('shapefile "' + CF + '" is not projected, and could not be imported to the GDB')  # log_it
                else:
                    shp_dict[CF]['GDBFC'] = outputFC = 'bas16_' + basid + '_changes_' + CT
                    if arcpy.Exists(FD+'\\'+outputFC):
                        try:
                            arcpy.Append_management(CF, FD+ '\\' +outputFC, 'TEST')
                        except:
                            errors.append("Feature Class " + outputFC + " might be missing data from Shapefile "
                                          + CF + " because their attributes did not line up exactly.")
                            arcpy.Append_management(CF, FD + '\\' +outputFC, 'NO_TEST')
                    else:
                        arcpy.FeatureClassToFeatureClass_conversion(CF, FD, outputFC)
        #counties = get_counties(list(x+'\\'+y for x,y in changeFiles), BAS14countyMerge)
        counties = get_counties(changeFiles, bas_yy_county_merge)
        import_support(GDB, counties, folder, state)
        lisrds(counties)
        mxd = GDB.replace('.gdb', '.mxd')
        shutil.copy(mxd_template, mxd)
        MXD = arcpy.mapping.MapDocument(mxd)
        layers = arcpy.mapping.ListLayers(MXD)
        for layer in layers:
            newfc = layer.datasetName.replace('template', basid)
            newpath = GDB+'\\'+newfc
            if layer.isFeatureLayer and arcpy.Exists(newpath):
                layer.replaceDataSource(GDB, "FILEGDB_WORKSPACE", newfc)
            layer.name = layer.name.replace('template', basid)
        DF = arcpy.mapping.ListDataFrames(MXD)[0]
        layers = arcpy.mapping.ListLayers(MXD)
        for layer in layers:
            if layer.isBroken:
                arcpy.mapping.RemoveLayer(DF, layer)
        countylyr = arcpy.mapping.ListLayers(MXD, 'bas_county', DF)[0]
        DF.extent = countylyr.getExtent()
        MXD.save()
        del MXD, DF
        log_it(conn, basid, filename, folder, state, subType, counties, errors, datetime.datetime.now(), shp_dict)
    except Exception, e:
        errors.append(e)
        log_it(conn, basid, filename, folder, state, subType, counties, errors, datetime.datetime.now(), shp_dict)


if __name__ == "__main__":  # script is being executed on its own, outside of idle.
    notify()
    inText = raw_input("Enter a BAS ID, or comma separated list of BAS IDs (with no spaces):\n")
    while 1:
        if inText:
            inList = inText.split(',')
            for entity in inList:
                runit(entity)
        else:
            break
        notify()
        repeat = raw_input("Done with list. Do you want to run more (y,n)?: ")
        if repeat.lower() in ['y', 'yes', '1']:
            notify()
            inText = raw_input("Enter a BAS ID, or comma separated list of BAS IDs (with no spaces):\n")
        else:
            break
