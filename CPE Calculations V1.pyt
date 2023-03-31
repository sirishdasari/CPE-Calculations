import arcpy
import pandas as pd
import datetime
import math
import time

class Toolbox(object):
    def __init__(self):
        self.label = "Toolbox"
        self.alias = "toolbox"
        self.tools = [MainsLeaksExtract,DataConditioning,Validation,Effectiveness,Whatif]
    
class MainsLeaksExtract(object):
    def __init__(self):
        self.label = "Data Conditioning Tool 1"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        cp = arcpy.Parameter(
            displayName = "Enter CP Zone Layer",
            name = "incp",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        cplist = arcpy.Parameter(
            displayName = "Enter CP Zone list",
            name = "mapCellKey",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        cplist.parameterDependencies = [cp.name]
        cplist.columns = [['String', 'MapCellKey'], ['String', 'HubName'],['String', 'TownName'], ['String', 'MapNumber']]
    
        mains = arcpy.Parameter(
            displayName = "Enter Mains layer",
            name = "infcs",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        mainsList = arcpy.Parameter(
            displayName = "Enter Mains list",
            name = "instDate",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")
        mainsList.parameterDependencies = [mains.name]
        mainsList.columns = [['String', 'Installation Date'], ['String', 'Nominal Diameter'], ['String', 'Coating Type'], ['String', 'Pressure Class'], ['String', 'Material GDO']]

        mainsExtract = arcpy.Parameter(
            displayName = "Enter the path mains extraction output",
            name = "mainsExtract",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Output")

        services = arcpy.Parameter(
            displayName = "Enter services Layer",
            name = "services",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        leaks = arcpy.Parameter(
            displayName="Enter Leaks Layer",
            name="leaks",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        leaksAttr = arcpy.Parameter(
            displayName = "Select Leakkey Attribute",
            name = "leaks_attribute",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input",
            multiValue = False)
        leaksAttr.parameterDependencies = [leaks.name]

        leaksFilter = arcpy.Parameter(
            displayName="Filter the Leak values",
            name="leaksFilter",
            datatype="GPSQLExpression",
            parameterType="Required",
            direction="Input")
        leaksFilter.parameterDependencies = [leaks.name]

        leaksExtraction = arcpy.Parameter(
            displayName = "Enter the path for leaks output",
            name = "leaksExtraction",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Output")
        
        return [cp,cplist,mains,mainsList,services,leaks,leaksAttr,leaksFilter,mainsExtract,leaksExtraction]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        cp=parameters[0]
        cplist=parameters[1]
        mains=parameters[2]
        mainsList=parameters[3]

        arcpy.env.workspace = cp.valueAsText
        if cp.altered:
            cplist.filters[0].list = [f.name for f in arcpy.ListFields(cp.valueAsText)]
            cplist.filters[1].list = [f.name for f in arcpy.ListFields(cp.valueAsText)]
            cplist.filters[2].list = [f.name for f in arcpy.ListFields(cp.valueAsText)]
            cplist.filters[3].list = [f.name for f in arcpy.ListFields(cp.valueAsText)]
        if mains.altered:
            mainsList.filters[0].list = [f.name for f in arcpy.ListFields(mains.valueAsText)]
            mainsList.filters[1].list = [f.name for f in arcpy.ListFields(mains.valueAsText)]
            mainsList.filters[2].list = [f.name for f in arcpy.ListFields(mains.valueAsText)]
            mainsList.filters[3].list = [f.name for f in arcpy.ListFields(mains.valueAsText)]
            mainsList.filters[4].list = [f.name for f in arcpy.ListFields(mains.valueAsText)]
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):

        # Extracting Mains
        self.MainsExtract(parameters[0].valueAsText,parameters[1].value[0],parameters[2].valueAsText,parameters[3].value[0])
        arcpy.management.CopyFeatures("in_memory/Mains_Extraction",parameters[8].valueAsText)

        # Extracting Leaks
        self.LeaksCalc(parameters[8].valueAsText,parameters[1].value[0][0],parameters[4].valueAsText,parameters[5].valueAsText,parameters[6].valueAsText,parameters[7].valueAsText,parameters[9].valueAsText)

    ########################## Mains Extraction ##################################
    def MainsExtract(self,layer_cp,layer_cp_fields,layer_mains,layer_mains_fields):
        
        footageLength = "CP_Zone_Length_ft"
        
        arcpy.AddMessage("Extracting Mains")

        #creating the duplicate layers
        arcpy.management.CopyFeatures(layer_cp,"in_memory/CP_Clean")
        arcpy.management.CopyFeatures(layer_mains,"in_memory/Mains_Clean")
        arcpy.management.DeleteField("in_memory/CP_Clean",layer_cp_fields,"KEEP_FIELDS")
        arcpy.management.DeleteField("in_memory/Mains_Clean",layer_mains_fields,"KEEP_FIELDS")
        
        # Rename field names which is in original file
        new_cp_fields=[[layer_cp_fields[0],'MapCellKey', 'MapCellKey'], 
                   [layer_cp_fields[1],'HubName', 'HubName'],
                   [layer_cp_fields[2],'TownName', 'TownName'], 
                   [layer_cp_fields[3],'MapNumber', 'MapNumber']]
        new_mains_fields = [[layer_mains_fields[0], 'Installation_Date','Installation Date'], 
                        [layer_mains_fields[1], 'Nominal_Diameter','Nominal Diameter'], 
                        [layer_mains_fields[2], 'External_Coating','External Coating'], 
                        [layer_mains_fields[3], 'Pressure_Class','Pressure Class'], 
                        [layer_mains_fields[4], 'Material','Material']]
        
        # Alter the field names to standard names
        for f in new_cp_fields:
            arcpy.management.AlterField("in_memory/CP_Clean", f[0], new_field_name =  f[1], new_field_alias=f[2])
        for f in new_mains_fields:
            arcpy.management.AlterField("in_memory/Mains_Clean", f[0], new_field_name =  f[1], new_field_alias=f[2])
        
        # Defining MapCellKey, CP Fields, and Mains Fields
        mapcellkey = new_cp_fields[0][1]
        cp_list = [cp[1] for cp in new_cp_fields]       # 'MapCellKey','HubName','TownName','MapNumber'
        mains_list = [m[1] for m in new_mains_fields]   # 'Installation_Date','Nominal_Diameter','External_Coating','Pressure_Class','Material_GDO'
        
        # Clip and spatial join 
        # Extracting the mains layer which are falling inside CP Zone layers
        # Assigning the MapCellKey to the mains layer 
        arcpy.analysis.Clip("in_memory/Mains_Clean","in_memory/CP_Clean","in_memory/clip") 
        arcpy.MultipartToSinglepart_management ("in_memory/clip", "in_memory/clip_out")
        arcpy.analysis.SpatialJoin("in_memory/clip_out","in_memory/CP_Clean","in_memory/clip_spatial","JOIN_ONE_TO_ONE",match_option="HAVE_THEIR_CENTER_IN")
        
        # Calculating the new footage length of the mains layer falling under CP Zone
        arcpy.management.AddField("in_memory/clip_spatial", footageLength, "DOUBLE",field_alias="CP Zone Length (ft)")
        arcpy.management.CalculateGeometryAttributes("in_memory/clip_spatial",[[footageLength,"LENGTH_GEODESIC"]],"FEET_US")
        
        # Creating a dataframe of mains layer
        data = [row for row in arcpy.da.SearchCursor("in_memory/clip_spatial",["OID@",mapcellkey,footageLength])]
        df = pd.DataFrame(data,columns=["OID",mapcellkey,footageLength])
        df1=df.groupby([mapcellkey,"OID"])[footageLength].max()
        d={f[1]:(f[0],f[2]) for f in data}
        
        # Extracting the max length of the mains layer
        # Extracting the OID of the mains layer which are having the max length
        l=[]
        for row in set(d.keys()):
            if row != None:
                dict = df1[row].to_dict()
                l.append(max(dict,key = dict.get))

        # Deleting the rows which are not having the max length of the mains layer for each MapCellKey
        with arcpy.da.UpdateCursor("in_memory/clip_spatial",["OBJECTID"]) as cursor:
            for row in cursor:
                if row[0] not in l:
                    cursor.deleteRow()
        
        # Deleting the unwanted fields from the mains layer
        # Calculating the new CP Zone LENGTH_FT length of the mains layer
        del_fields = cp_list + mains_list+[footageLength] # reusing CP Zone LENGTH_FT field to calculate CP Zone Length instead of creating new field
        arcpy.management.JoinField("in_memory/CP_Clean",mapcellkey,"in_memory/clip_spatial",mapcellkey)
        arcpy.management.DeleteField("in_memory/CP_Clean",del_fields,"KEEP_FIELDS")
        arcpy.management.CalculateGeometryAttributes("in_memory/CP_Clean",[[footageLength,"LENGTH_GEODESIC"]],"FEET_US")
        arcpy.management.CopyFeatures("in_memory/CP_Clean","in_memory/Mains_Extraction")

        ## Updating the default values
        with arcpy.da.UpdateCursor("in_memory/Mains_Extraction",mains_list+[footageLength]) as cursor:
            for row in cursor:
                row[5]=round(row[5],6)
                if row[0] == None:
                    row[0] = time.strftime('1/1/1900 12:00:00 AM')
                else: 
                    if row[0].year <1900:
                        row[0] = time.strftime('1/1/1900 12:00:00 AM')
                if row[1] == None:
                    row[1] = 2
                if row[2] == None or row[2] == "N/A Plastic":
                    row[2] = "Mill Wrap"
                if row[3]==None:
                    row[3] = "IP (1 - 60 psig)"
                if row[3]=="Unknown":
                    row[3] = "IP (1 - 60 psig)"
                if row[4] == None:
                    row[4] = "Steel"
                elif row[4] in ["Unknown","PE","HDPE","MDPE","Plastic PE","Plastic Other","Poly (Mid-Tex)","Poly Vinyl Chloride"]:
                    row[4] = "Steel"
                else:
                    pass
                cursor.updateRow(row)
        
        return "in_memory/Mains_Extraction"
    ######################### Leaks Extraction ##################################
    def LeaksCalc(self,mainsExtract,mapcellkey,layer_services,layer_leaks,layer_leaks_leakKey,layer_leaks_filter,leaks):
        arcpy.AddMessage("Extracting Leaks")
        
        mapcellkey = mapcellkey

        arcpy.management.CopyFeatures(mainsExtract,"in_memory/Mains_Extraction")
        arcpy.management.CopyFeatures(layer_services ,"in_memory/Services")
        arcpy.management.CopyFeatures(layer_leaks ,"in_memory/Leaks_excel")

        ## ANALYSIS: Spatial Join and Select by Attributes for notnull values
        arcpy.analysis.SpatialJoin("in_memory/Services","in_memory/Mains_Extraction","in_memory/sj_Services","JOIN_ONE_TO_ONE",match_option="BOUNDARY_TOUCHES")
        arcpy.SelectLayerByAttribute_management("in_memory/sj_Services", "ADD_TO_SELECTION",'"{}" IS NOT NULL'.format(mapcellkey))
        arcpy.management.CopyFeatures("in_memory/sj_Services" ,"in_memory/Services_Final")
        arcpy.analysis.Near("in_memory/Leaks_excel",["in_memory/Mains_Extraction","in_memory/Services_Final"],method = "GEODESIC")

        ##Leaks Output
        arcpy.management.CopyFeatures("in_memory/Leaks_excel","in_memory/Leaks_update")

        with arcpy.da.UpdateCursor("in_memory/Leaks_update",["NEAR_FC"]) as cursor:
            for row in cursor:
                if row[0] != None:
                    if row[0]=="in_memory/Services_Final":
                        row[0]="Service"
                    elif row[0]=="in_memory/Mains_Extraction":
                        row[0]="CP_Zone"
                    cursor.updateRow(row)
 
        del cursor

        # Filtering the data based on the conditions (probable source, repaired on, corrosion and near distance=5)
        filterData = arcpy.SelectLayerByAttribute_management("in_memory/Leaks_update", "NEW_SELECTION","""{0}""".format(layer_leaks_filter+' And NEAR_DIST > 0 And NEAR_DIST <= 5'))
        arcpy.management.CopyFeatures(filterData ,"in_memory/Leaks_excel_Final")

        ##Updating the near mapcellkey value to dictionary
        arcpy.management.AddField("in_memory/Leaks_excel_Final","Near_MapCellKey","LONG")
        update_service = {f[0]:(f[1]) for f in arcpy.da.SearchCursor("in_memory/Services_Final",["OID@",mapcellkey])}
        update_cp_zone = {f[0]:(f[1]) for f in arcpy.da.SearchCursor("in_memory/Mains_Extraction",["OID@",mapcellkey])}


        with arcpy.da.UpdateCursor("in_memory/Leaks_excel_Final", ["NEAR_FC","NEAR_FID","Near_MapCellKey"]) as cursor:
            for row in cursor:
                try:
                    if row[0] == "CP_Zone":
                        row[2] = update_cp_zone[row[1]]
                    elif row[0] == "Service":
                        row[2] = update_service[row[1]]
                    cursor.updateRow(row)
                except:
                    pass
        del cursor

        # Updating the Corrosion leaks and All other leaks to leaks layer
        leakkey={f[0]:(f[1],f[2]) for f in arcpy.da.SearchCursor("in_memory/Leaks_excel_Final",[layer_leaks_leakKey,"Near_MapCellKey","NEAR_FC"])}
        arcpy.management.AddField("in_memory/Leaks_update", "Leak_MapCellKey", "LONG") 
        arcpy.management.AddField("in_memory/Leaks_update", "NEAR_FC", "TEXT")
        arcpy.management.AddField("in_memory/Leaks_update", "CP_Leak_Type", "TEXT")
        with arcpy.da.UpdateCursor("in_memory/Leaks_update", [layer_leaks_leakKey,"Leak_MapCellKey","NEAR_FC","CP_Leak_type"]) as cursor:
            for row in cursor:
                try:
                    row[1] = leakkey[row[0]][0]
                    row[2] = leakkey[row[0]][1]
                    if row[1] is not None:
                        row[3] = "Corrosion Leaks"            
                except:
                    row[3] = "All Other Leaks"
                cursor.updateRow(row)
        del cursor
        with arcpy.da.UpdateCursor("in_memory/Leaks_update", [layer_leaks_leakKey,"Leak_MapCellKey","NEAR_FC","CP_Leak_type"]) as cursor:
            for row in cursor:
                if row[1] is None:
                    row[2] = None
                cursor.updateRow(row)

        data = [row for row in arcpy.da.SearchCursor("in_memory/Leaks_update",["NEAR_FC","Leak_MapCellKey"])]
        fc_dataframe = pd.DataFrame(data,columns=["leaks","MapCellKey"]).set_index("MapCellKey")
        res = fc_dataframe.groupby(["MapCellKey","leaks"]).size()
        fc = res.to_dict()

        #updating the leak on Mains/Service 
        arcpy.management.AddField(mainsExtract, "Corrosion Leak On Mains", "LONG")
        arcpy.management.AddField(mainsExtract, "Corrosion Leak On Services", "LONG")
        arcpy.management.AddField(mainsExtract, "Corrosion Leaks/CP Zone", "LONG")
        with arcpy.da.UpdateCursor(mainsExtract, [mapcellkey,"Corrosion_Leak_On_Mains","Corrosion_Leak_On_Services", "Corrosion_Leaks_CP_Zone"]) as cursor:
            for row in cursor:
                try:
                    cp,service = 0,0
                    if (row[0],"CP_Zone") in fc:
                        row[1] = fc[(row[0],"CP_Zone")]
                        cp = row[1]
                    if (row[0],"Service") in fc:
                        row[2] = fc[(row[0],"Service")]
                        service = row[2]
                    if cp > 0 or service > 0:
                        row[3] = cp + service
                    cursor.updateRow(row)
                except:
                    pass

        del cursor
        arcpy.management.CopyFeatures("in_memory/Leaks_update",leaks)
        return 
    
# DataConditioning Tool
class DataConditioning(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Data Conditioning Tool 2"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        mainsExtract = arcpy.Parameter(
            displayName = "Enter Mains Extract layer",
            name = "mainsExt",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        mainsMCK = arcpy.Parameter(
            displayName = "Enter Mains extract MapCellKey attribute",
            name = "instDate",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        mainsMCK.parameterDependencies = [mainsExtract.name]

        wo_tbl = arcpy.Parameter(
            displayName = "Enter the Work Order table",
            name = "wo_tbl",
            datatype = "DETable",
            parameterType = "Required",
            direction = "Input")
            
        woField = arcpy.Parameter(
            displayName='Enter Field Name',
            name='woField',
            datatype='GPString',
            parameterType='Required',
            direction='Input')
        woField.columns = [['GPString', 'MapCellKey'], ['GPString', 'WorkOrderNumber'], ['GPString', 'RAnodeNumber']]
        woField.parameterDependencies = [wo_tbl.name]

        anodeGIS = arcpy.Parameter(
            displayName = "Enter the Anode GIS Layer",
            name = "anodeGIS",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        soil = arcpy.Parameter(
            displayName = "Enter Soil Layer",
            name = "soil",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        soilAttr = arcpy.Parameter(
            displayName = "Enter Ratings Attribute to assign",
            name = "soil_attribute",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        soilAttr.parameterDependencies = [soil.name]

        dataConditioning = arcpy.Parameter(
            displayName = "Enter the path for extraction output",
            name = "dataConditioning",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Output")

        
        return [mainsExtract,mainsMCK,wo_tbl,woField,anodeGIS,soil,soilAttr,dataConditioning]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        wo_tbl = parameters[2]
        woField = parameters[3]
        if wo_tbl.altered:
            woField.filters[0].list = [f.name for f in arcpy.ListFields(wo_tbl.valueAsText)]
            woField.filters[1].list = [f.name for f in arcpy.ListFields(wo_tbl.valueAsText)]
            woField.filters[2].list = [f.name for f in arcpy.ListFields(wo_tbl.valueAsText)]
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):        
        self.dataConditionProcess(parameters[0].valueAsText,parameters[1].valueAsText,parameters[2].valueAsText,parameters[3].valueAsText,parameters[4].valueAsText,parameters[5].valueAsText,parameters[6].valueAsText)
        arcpy.management.CopyFeatures("in_memory/Extraction",parameters[7].valueAsText)

    # Data Conditioning Function
    def dataConditionProcess(self,mainsExtraction,mainsExtractionMCK,WOTable,WOTableFields,layer_anodeGIS,layer_soil,soilRating):
        
        arcpy.management.CopyFeatures(mainsExtraction,"in_memory/Extraction")
        arcpy.analysis.Intersect(["in_memory/Extraction",layer_soil],"in_memory/CP_Soil_intersect","ALL","#","LINE")

        mapcellkey = mainsExtractionMCK
        rating = soilRating
        soil_new = [mapcellkey,rating,"CP_Zone_LENGTH_FT"]

        # Calculate length of intersected line (new length after intersection) with the soil
        arcpy.management.CalculateGeometryAttributes("in_memory/CP_Soil_intersect",[["CP_Zone_LENGTH_FT","LENGTH_GEODESIC"]],"FEET_US")
        
        #Give the default for null attributes
        with arcpy.da.UpdateCursor("in_memory/CP_Soil_intersect",rating) as cursor:
            for row in cursor: 
                if row[0] is None:
                    row[0] = "Default"
                cursor.updateRow(row)
        del cursor

        # Convert to dataframe and find the largest length of soil attribute to assign to MapcellKey         
        data = [x for x in arcpy.da.SearchCursor("in_memory/CP_Soil_intersect",soil_new)]
        df = pd.DataFrame(data,columns=soil_new)
        df1=df.groupby([mapcellkey,rating])["CP_Zone_LENGTH_FT"].sum()
        keys = [x[0] for x in arcpy.da.SearchCursor("in_memory/CP_Soil_intersect",mapcellkey)]
        ratingData = {}
        for key in set(keys):
            dicty = df1[key].to_dict()
            ratingData[key] = max(dicty,key = dicty.get)

        #Add Field names
        arcpy.management.AddFields("in_memory/Extraction", [["Soil_Rating", "TEXT","Soil Rating"],
                                                            ["Work_Orders", "SHORT","Work Orders"],
                                                            ["No_Anode_Number_CM", "SHORT","No Anode Number (CM+)"],
                                                            ["Anodes_Installed_CP_Zone_GIS", "SHORT","Anodes Installed/CP Zone (GIS)"],
                                                            ["Zonekeycount", "SHORT","Zonekeycount"],
                                                            ["Anodes_Installed_Max_between_CM_and_GIS","SHORT","Anodes Installed (Max between CM+ and GIS)"]])
        # Performing Calculations on Work Order
        totaldata = WOTableFields.split(" ")
        xlfields = [totaldata[0] ,totaldata[1]]
        anode = [totaldata[0] ,totaldata[1],totaldata[2]]
        
        # converting Table data to pandas
        xl_data = [x for x in arcpy.da.SearchCursor(WOTable, xlfields)]
        df = pd.DataFrame(xl_data,columns=xlfields)
        df1=df.groupby(xlfields[0])[xlfields[1]].apply(list)
        
        #Getting work order unique count
        WOcountData = {}
        for f in df1.to_dict():
            WOcountData[int(f)] = len(set(df1[f]))
        
        #Getting Anode Excel count
        RAcountData={}
        pd_data = [x for x in arcpy.da.SearchCursor(WOTable, anode)]
        dframe = pd.DataFrame(pd_data,columns=anode).fillna(0)
        dframe1=dframe.groupby([totaldata[0],totaldata[1]])[totaldata[2]].unique()
        dframe2=dframe1.reset_index()

        # Convert to int64 and get the count
        dframe2[totaldata[2]] = dframe2[totaldata[2]].astype("int64")
        dframe3 = dframe2.groupby([totaldata[0]])[totaldata[2]].sum()

        anodeDict = dframe3.to_dict()
        for f in anodeDict:
            RAcountData[int(f)] = int(anodeDict[f])

        #Assign Soil Rating to CP Zone Layer
        with arcpy.da.UpdateCursor("in_memory/Extraction",[mapcellkey,"Soil_Rating"]) as cursor:
            for row in cursor:
                if row[0] in ratingData.keys():
                    row[1] = ratingData[row[0]]
                cursor.updateRow(row)
        del cursor

        # Getting anodeGIS count
        arcpy.analysis.SpatialJoin(layer_anodeGIS,mainsExtraction,"in_memory/anode_count","JOIN_ONE_TO_ONE","KEEP_ALL","","INTERSECT")
        anodedata = [row for row in arcpy.da.SearchCursor("in_memory/anode_count",[mainsExtractionMCK])]
        df = pd.DataFrame(anodedata,columns=[mainsExtractionMCK])
        anodegiscount = df.groupby([mainsExtractionMCK])[mainsExtractionMCK].count().to_dict()

        # Assign Anode, WorkOrder to CP Zone layer
        with arcpy.da.UpdateCursor("in_memory/Extraction",[mapcellkey,"Work_Orders","No_Anode_Number_CM","Anodes_Installed_CP_Zone_GIS","Anodes_Installed_Max_between_CM_and_GIS"]) as cursor:
            for row in cursor:
                if row[0] in WOcountData.keys():
                    row[1] = WOcountData[row[0]]
                if row[0] in RAcountData.keys():
                    row[2] = RAcountData[row[0]]
                if row[0] in anodegiscount.keys():
                    row[3] = anodegiscount[row[0]]
                row[4] = Score.AnodeGreater(row[2],row[3])
                cursor.updateRow(row)
        del cursor
        return "in_memory/Extraction"

# Effectiveness Tool
class Effectiveness(object):
    def __init__(self):
        self.label = "Scores Effectiveness Calculations"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        cp = arcpy.Parameter(
            displayName = "Enter the output from Data Conditioning",
            name = "incp",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")

        reading_tbl = arcpy.Parameter(
            displayName = "Enter CP Reading table",
            name = "reading_tbl",
            datatype = "DETable",
            parameterType = "Required",
            direction = "Input")

        tblField = arcpy.Parameter(
            displayName='Enter Field Name',
            name='tblField',
            datatype='GPString',
            parameterType='Required',
            direction='Input')
        tblField.columns = [['GPString', 'MapCellKey'], ['GPString', 'Zone Key'], ['GPString', 'Reading'],['GPString', 'Completion Date']]
        tblField.parameterDependencies = [reading_tbl.name]
 
        gdb = arcpy.Parameter(
            displayName="Input GeoDatabase Path",
            name="in_workspace",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        yrbtwn = arcpy.Parameter(
            displayName = "Select last 5 years Test point reading data",
            name = "yrbtwn",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")
        yr = datetime.datetime.now().year
        yrbtwn.filter.list = [f'{yr-4} to {yr}',f'{yr-5} to {yr-1}',f'{yr-6} to {yr-2}',f'{yr-7} to {yr-3}',f'{yr-8} to {yr-4}']
        
        guidelines = arcpy.Parameter(
            displayName = "Enter Guidelines Excel file",
            name = "guidelines",
            datatype = "DEFile",
            parameterType = "Optional",
            direction = "Input")
        guidelines.filter.list = ['xlsx','xls']
        return [cp,reading_tbl,tblField,yrbtwn,gdb,guidelines]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        cp=parameters[0]
        tbl = parameters[1]
        tbl_fld = parameters[2]
        arcpy.env.workspace = cp.valueAsText
        if tbl.altered:
            tbl_fld.filters[0].list = [f.name for f in arcpy.ListFields(tbl.valueAsText)]
            tbl_fld.filters[1].list = [f.name for f in arcpy.ListFields(tbl.valueAsText)]
            tbl_fld.filters[2].list = [f.name for f in arcpy.ListFields(tbl.valueAsText)]
            tbl_fld.filters[3].list = [f.name for f in arcpy.ListFields(tbl.valueAsText)]
        return

    def updateMessages(self, parameters):
        if parameters[2].altered:
            if len(parameters[2].valueAsText.split(" ")) != 4:
                parameters[2].setWarningMessage('Remove space if present in field names')
            else:
                parameters[2].clearMessage()
        return

    def execute(self, parameters, messages):
        # Adding the excel input functionality
        self.OCost = []
        self.RCost = []
        self.performanceXL = []
        self.complianceXL = []
        self.susceptibilityXL = []
        self.costXL = []
        if parameters[5].valueAsText != None:
            OC_DFguidelines = pd.read_excel(parameters[5].valueAsText,sheet_name='Operations Cost')
            RC_DFguidelines = pd.read_excel(parameters[5].valueAsText,sheet_name='Replacement Pipe Cost')
            PXL_DFguidelines = pd.read_excel(parameters[5].valueAsText,sheet_name='Performance')
            CoXL_DFguidelines = pd.read_excel(parameters[5].valueAsText,sheet_name='Compliance')
            SXL_DFguidelines = pd.read_excel(parameters[5].valueAsText,sheet_name='Susceptibility')
            CXL_DFguidelines = pd.read_excel(parameters[5].valueAsText,sheet_name='Cost')
            self.OCost = [float(f[1]) for f in OC_DFguidelines.values]
            self.RCost = [(float(f[0]),float(f[1])) for f in RC_DFguidelines.values]
            self.performanceXL = [float(f[1]) for f in PXL_DFguidelines.values]
            self.complianceXL = [float(f[1]) for f in CoXL_DFguidelines.values]
            self.susceptibilityXL = [float(f[1]) for f in SXL_DFguidelines.values]
            self.costXL = [float(f[1]) for f in CXL_DFguidelines.values]

        # Year Today and generate last 5 years interval
        yr = datetime.datetime.now().year
        ind = [f'{yr-4} to {yr}',f'{yr-5} to {yr-1}',f'{yr-6} to {yr-2}',f'{yr-7} to {yr-3}',f'{yr-8} to {yr-4}'].index(parameters[3].valueAsText)
        x = datetime.datetime.now().year-ind
        self.lastfiveyears = [x-4,x-3,x-2,x-1,x]
        arcpy.AddMessage(self.lastfiveyears)
        self.datacondition = parameters[0].valueAsText
        self.dcfields = ['MapCellKey','Installation_Date','Nominal_Diameter','External_Coating','Material']
        self.tbl = parameters[1].valueAsText
        self.tblfields = parameters[2].valueAsText.split(" ")
        self.yearRange = parameters[3].valueAsText

        # # Reading Table calculations
        self.ReadingTable()
        arcpy.TableToGeodatabase_conversion("in_memory/ReadingTable",parameters[4].valueAsText)
        arcpy.management.CopyFeatures("in_memory/forcalculation",parameters[4].valueAsText+"\\"+"DataCondition")
        arcpy.conversion.TableToTable("in_memory/forcalculation", "in_memory", "Calculation")

        # Performance calculations
        self.PerformanceCalc()
        arcpy.TableToGeodatabase_conversion("in_memory/Performance",parameters[4].valueAsText)

        #Compliance calculations
        self.ComplianceCalc()
        arcpy.TableToGeodatabase_conversion("in_memory/Compliance",parameters[4].valueAsText)

        #Susceptibility calculations
        self.SusceptibilityCalc()
        arcpy.TableToGeodatabase_conversion("in_memory/Susceptibility",parameters[4].valueAsText)

        # #Cost calculations
        self.CostCalc()
        arcpy.TableToGeodatabase_conversion("in_memory/Cost",parameters[4].valueAsText)

        # TotalEffectivenessCalc calculations
        self.TotalEffectivenessCalc()
        arcpy.env.workspace = parameters[4].valueAsText
        arcpy.management.CopyFeatures("in_memory/TotalEffectiveness","AE_CP_Zone")

    ########################## ReadingTable ##################################
    def ReadingTable(self):
        mapcellkeyLyr = self.dcfields[0]
        TableField = self.tblfields
        mck_tbl_fld = TableField[0]
        zonekey_tbl_fld = TableField[1]

        arcpy.AddMessage("Extracting Reading Table")
        years_int = self.lastfiveyears
        
        # Create an empty table
        tableCalcs = arcpy.management.CreateTable("in_memory","ReadingTable")
        
        # Convert excel to table
        arcpy.TableToTable_conversion(self.tbl, "in_memory", "reading")
        
        # Add Test_Reading field and convert values to float object
        arcpy.management.AddField("in_memory/reading", "Test_Reading", "DOUBLE")
        with arcpy.da.UpdateCursor("in_memory/reading",TableField+["Test_Reading"]) as cursor:
            for row in cursor:
                try:
                    row[4] = float(row[2])
                except:
                    pass
                cursor.updateRow(row)
        del cursor

        # Convert table to pandas data frame 
        TableField[2] = "Test_Reading"
        reading_data = [x for x in arcpy.da.SearchCursor("in_memory/reading",TableField)]
        df = pd.DataFrame(reading_data,columns=TableField)
        df['YearOfCompletion'] = df[TableField[3]].apply(lambda x: x.year)
        df2 = df[[mck_tbl_fld,zonekey_tbl_fld,"Test_Reading",'YearOfCompletion']]
        df3 = df2.pivot_table(index=[mck_tbl_fld,zonekey_tbl_fld],columns = "YearOfCompletion",values = "Test_Reading",aggfunc='min').reset_index()
        
        # Get all years in pivot table
        years_list = [f for f in set(df["YearOfCompletion"].tolist())] 
        
        # Remove years present in given input and then remove all the years excluding the given input
        try:
            for f in years_int:
                years_list.remove(f)
        except:
            arcpy.AddError("Index out of selected range")
            quit()

        # Drop all the years in pivot table except the input years
        df3.drop(years_list,axis=1,inplace=True)
        dict = {f:("Year_"+str(f)) for f in years_int}
        df3.rename(columns=dict,inplace=True)

        arcpy.management.AddField(tableCalcs,mck_tbl_fld,"LONG")
        arcpy.management.AddField(tableCalcs,zonekey_tbl_fld,"LONG")
        
        # Add the column names to Table
        for f in df3.columns.to_list():
            if f not in [mck_tbl_fld,zonekey_tbl_fld]:
                arcpy.management.AddField(tableCalcs,f,"DOUBLE")
        
        exceldata = df3.fillna(0)
        
        # asign value for Years Non-Compliant
        less = []
        for f in years_int:
            exceldata["Fails_850mV_"+str(f)]= exceldata["Year_"+str(f)].apply(lambda x : 1 if x >= -0.849 else 0)
            arcpy.management.AddField(tableCalcs,"Fails_850mV_"+str(f),"DOUBLE")
            less.append("Fails_850mV_"+str(f))

        # assign value for Years Meet Criteria
        greater = []
        for f in years_int: 
            exceldata["Fails_1100mV_"+str(f)]= exceldata["Year_"+str(f)].apply(lambda x : 1 if x <= -1.1 else 0)
            arcpy.management.AddField(tableCalcs,"Fails_1100mV_"+str(f),"DOUBLE")
            greater.append("Fails_1100mV_"+str(f))
            
        # Add Total Years Non-Compliant and Years meet criteria
        exceldata["Total_Fails_850mV"] = exceldata[less].sum(axis=1)
        arcpy.management.AddField(tableCalcs,"Total_Fails_850mV","DOUBLE")
        exceldata["Total_Fails_1100mV"] = exceldata[greater].sum(axis=1)
        arcpy.management.AddField(tableCalcs,"Total_Fails_1100mV","DOUBLE")

        # insert all data to table from pandas dataframe
        with arcpy.da.InsertCursor(tableCalcs,exceldata.columns.to_list()) as cursor:
            for row in exceldata.values.tolist():
                cursor.insertRow(row)

        # Delete rows if all years contain Null values
        with arcpy.da.UpdateCursor(tableCalcs,["Year_"+str(f) for f in years_int]) as cursor:
            for row in cursor:
                if row[0] is None and row[1] is None and row[2] is None and row[3] is None:
                    cursor.deleteRow()
        del cursor

        # Get Total Years Non-Compliant, Years meet criteria and Zonekey count
        reading_sum_count_data=exceldata.groupby(exceldata[mck_tbl_fld]).aggregate({'Total_Fails_850mV':"sum",'Total_Fails_1100mV':"sum",zonekey_tbl_fld:"count"}).reset_index()
        self.voltReadCount = {}
        for f in reading_sum_count_data.index:
            self.voltReadCount[int(reading_sum_count_data[mck_tbl_fld][f])]=([reading_sum_count_data["Total_Fails_850mV"][f],reading_sum_count_data["Total_Fails_1100mV"][f],reading_sum_count_data["ZoneKey"][f]])

        # Update Total Readings (0.850v & 1.1v) 
        arcpy.management.CopyFeatures(self.datacondition, "in_memory/forcalculation")
        arcpy.management.AddField("in_memory/forcalculation","Years_Non_Compliant_850_Criteria","SHORT",field_alias="Years Non-Compliant -850 Criteria")
        arcpy.management.AddField("in_memory/forcalculation","Years_Meet_1100_Criteria","SHORT",field_alias="Years Meet -1100 Criteria")
        arcpy.management.AddField("in_memory/forcalculation","Years_Between_850_and_1100_Criteria","SHORT",field_alias="Years Between -850 and -1100 Criteria")
        with arcpy.da.UpdateCursor("in_memory/forcalculation",[mapcellkeyLyr,"Years_Non_Compliant_850_Criteria","Years_Meet_1100_Criteria","Zonekeycount","Years_Between_850_and_1100_Criteria"]) as cursor:
            for row in cursor:
                if row[0] in self.voltReadCount.keys():
                    row[3] = self.voltReadCount[row[0]][2]
                    if self.voltReadCount[row[0]][2] !=0 and self.voltReadCount[row[0]][1] !=None and self.voltReadCount[row[0]][2] !=None:
                        row[1] = math.ceil(self.voltReadCount[row[0]][0]/self.voltReadCount[row[0]][2])
                        row[2] = math.floor(self.voltReadCount[row[0]][1]/self.voltReadCount[row[0]][2])
                        row[4] = 5-(row[1]+row[2])
                elif row[0] not in self.voltReadCount.keys():
                    row[1] = 0
                    row[2] = 5
                    row[3] = 1
                    row[4] = 0
                cursor.updateRow(row)
        del cursor
        return
    
    ########################## PerformanceCalc ##################################
    def PerformanceCalc(self):
        self.Years_Non_Compliant = "Years_Non_Compliant_850_Criteria"
        self.Years_Meet_Criteria = "Years_Meet_1100_Criteria"
        arcpy.AddMessage("Extracting Performance Data")               
        arcpy.management.CopyRows("in_memory/Calculation", "in_memory/Performance")
        mapcellkey = self.dcfields[0]
        coating = self.dcfields[3]
        dateInst = self.dcfields[1]
        leakCount = "Corrosion_Leaks_CP_Zone"
        wo = "Work_Orders"
        anode = "Anodes_Installed_Max_between_CM_and_GIS"
        cp_length = "CP_Zone_Length_ft" 

        arcpy.management.AddFields("in_memory/Performance",[
            ["Distance_Correction_Factor_1000","DOUBLE","Distance Correction Factor (1000')"],
            ["Corrosion_Leaks_CP_Zone_Mains_and_Services","SHORT","Corrosion Leaks/CP Zone (Mains and Services)"],
            ["Work_Orders_CP_Zone","SHORT","Work Orders/CP Zone"],
            ["Anodes_Installed_CP_Zone","SHORT","Anodes Installed/ CP Zone"],
            ["Coating_Type","SHORT","Coating Type"],
            ["Pipe_Age","SHORT","Pipe Age"],
            ["Level_of_CP_CP_Zone","SHORT","Level of CP/CP Zone"],
            ["CP_Zone_Size_Footage","SHORT","CP Zone Size (Footage)"],
            ["Distribution_Performance_Factor_MAX22","SHORT","Distribution Performance Factor (MAX 22)"],
            ["Performance_Category","TEXT","Performance Category"]
            ])

        fields = [mapcellkey]+[
            leakCount,"Corrosion_Leaks_CP_Zone_Mains_and_Services",wo,"Work_Orders_CP_Zone",anode,
            "Anodes_Installed_CP_Zone",coating, "Coating_Type",dateInst,"Pipe_Age",
            self.Years_Non_Compliant,self.Years_Meet_Criteria,"Level_of_CP_CP_Zone",cp_length,"CP_Zone_Size_Footage",
            "Distribution_Performance_Factor_MAX22","Performance_Category","Distance_Correction_Factor_1000"]

        self.performanceTable = {}
        with arcpy.da.UpdateCursor("in_memory/Performance",fields) as cursor:
            for row in cursor:
                # getting the data from Scores Class
                row[2] = Score.CorrosionLeaksOnCPZone(row[1])
                row[4] = Score.WorkOrders(row[3])
                row[6] = Score.AnodesInstalledCPZone(row[5])
                row[8] = Score.CoatingType(row[7]) 
                row[10] = Score.PipeAgeScore(row[9])
                row[13] = Score.LevelOfCPZone(row[11],row[12])
                row[15] = Score.CPZoneSize(row[14])
                add = [row[2],row[4],row[6],row[8],row[10],row[13],row[15]]
                row[16] = 0
                for f in add:
                    if f != None:
                        row[16] += f
                row[17] = Score.PerformanceCategory(row[16],self.performanceXL)
                if row[14]!=0 or row[14]!=None: 
                    row[18] = 1000/row[14]
                self.performanceTable[row[0]]=(row[2],row[4],row[6],row[8],row[10],row[13],row[15],row[16],row[17])
                cursor.updateRow(row)
        del cursor
        
        arcpy.management.AlterField("in_memory/Performance", "Zonekeycount", "No_of_Test_Points","No. of Test Points")
        arcpy.management.DeleteField("in_memory/Performance",["HubName"])
        return "in_memory/Performance"
    
    ########################## ComplianceCalc ##################################
    def ComplianceCalc(self):
        arcpy.AddMessage("Extracting Compliance Data")
        arcpy.management.CopyRows("in_memory/Calculation", "in_memory/Compliance")
        
        # Convert CP Reading Table to pandas Data Frame
        fields = self.tblfields
        data = [f for f in arcpy.da.SearchCursor("in_memory/reading",fields)]
        df = pd.DataFrame(data,columns=fields)
        years_list = self.lastfiveyears
        
        zonekeys = []
        zk = df[fields[1]].unique().tolist()

        ## Finding greater than 455 days
        for z in zk:
            years = sorted(df[df[fields[1]]==z][fields[3]].to_list())
            length = len(years)
            i=0
            while i<length-1:
                if (years[i+1]-years[i]).days >455 and years[i].year in years_list:
                    zonekeys.append(z)
                i+=1
            
        dframe1=df.groupby([fields[1]])[fields[0]].unique()
        dict = dframe1.to_dict()

        mck=[]
        for f in zonekeys:
            mck.append(int(dict[f][0]))

        arcpy.AddMessage("MapCellKey >455 days: ")
        arcpy.AddMessage(list(set(mck)))

        arcpy.management.AddFields("in_memory/Compliance",[["Years_Meeting_Criteria_TP","SHORT","Years Meeting Criteria (TP)"],
                                                        ["Years_Meeting_Monitor_Schedule_TP","SHORT","Years Meeting Monitor Schedule (TP)"],
                                                        ["Distibution_Test_Station_Monitored_on_Schedule_Score","SHORT","Distibution Test Station Monitored on Schedule Score"],
                                                        ["Distribution_Test_Station_Meets_Criteria_Score","SHORT","Distribution Test Station Meets Criteria Score"],
                                                        ["Distribution_Compliance_Factor_MAX2","SHORT","Distribution Compliance Factor (MAX 2)"],
                                                        ["Compliance_Category","TEXT","Compliance Category"]])

        self.complianceTable = {}
        with arcpy.da.UpdateCursor("in_memory/Compliance",
                                    [self.Years_Non_Compliant,
                                    "Years_Meeting_Criteria_TP",
                                    "Years_Meeting_Monitor_Schedule_TP",
                                    "Distibution_Test_Station_Monitored_on_Schedule_Score",
                                    "Distribution_Test_Station_Meets_Criteria_Score",
                                    "Distribution_Compliance_Factor_MAX2",
                                    self.dcfields[0],
                                    "Compliance_Category"
                                    ]) as cursor:
            for row in cursor:
                if row[0] ==None:
                    row[1] = 5
                else:
                    row[1] = 5-row[0]
                if row[6] in mck:
                    row[2] = 4
                else:
                    row[2] = 5
                    
                if row[2] == 5:
                    row[3] = 0
                else:
                    row[3] = 1
                if row[1] == 5:
                    row[4] = 0
                else:
                    row[4] = 1
                row[5] = row[3] + row[4]    
                row[7] = Score.ComplianceCategory(row[5],self.complianceXL)
                self.complianceTable[row[6]]=(row[3],row[4],row[5],row[7])
                cursor.updateRow(row)
                
        arcpy.management.AlterField("in_memory/Compliance", "Zonekeycount", "No_of_Test_Points","No. of Test Points")
        return "in_memory/Compliance"
    
    ########################## SusceptibilityCalc ##################################
    def SusceptibilityCalc(self):
        arcpy.AddMessage("Extracting Susceptibility Data")
        arcpy.management.CopyRows("in_memory/Calculation", "in_memory/Susceptibility")
        fields = [
            ["Soil_Resistivity_ohm_cm",                                          "SHORT",     "Soil Resistivity (ohm-cm)"],                                              #0                                                       
            ["Distance_Factor_for_Corrosion_Leaks_1000",                         "DOUBLE",     "Distance Factor for Corrosion Leaks (1000')"],                           #1                                                                           
            ["Diameter_ft",                                                      "DOUBLE",     "Diameter (ft)"],                                                         #2                                           
            ["k_Factor",                                                         "DOUBLE",     "k Factor"],                                                              #3                                       
            ["idensity_mA_ft",                                                   "DOUBLE",     "idensity (mA/ft2)"],                                                     #4                                               
            ["ff_Coating_Effectiveness",                                         "DOUBLE",     "ff - Coating Effectiveness"],                                            #5                                                           
            ["fi",                                                               "DOUBLE",     "fi"],                                                                    #6                                   
            ["Delta_f",                                                          "DOUBLE",     "Δf"],                                                                    #7                                   
            ["tdl",                                                              "SHORT",     "tdl"],                                                                    #8                                   
            ["Recorded_Installation_Year",                                       "SHORT",     "Recorded Installation Year"],                                             #9                                                           
            ["Estimated_Install_Year",                                           "SHORT",     "Estimated Install Year"],                                                 #10                                                       
            ["Actual_Coating_Age",                                               "SHORT",     "Actual Coating Age"],                                                     #11                                                   
            ["Change_in_Coating_Effectiveness_Change_from_Initial_until_Today",  "DOUBLE",     "Change in Coating Effectiveness (Change from Initial until Today)"],     #12                                                                                               
            ["Coating_Effectiveness_Remaining",                                  "DOUBLE",     "Coating Effectiveness  Remaining"],                                      #13                                                               
            ["Coating_Effectiveness_Remaining_Percentage",                       "DOUBLE",     "Coating Effectiveness  Remaining - Percentage"],                         #14                                                                           
            ["Itotal_A",                                                         "DOUBLE",     "Itotal (A)"],                                                            #15                                           
            ["Magnesium_Anode_Constant",                                         "LONG",       "Magnesium Anode Constant"],                                              #16                                                       
            ["Magnesium_Factor_f",                                               "DOUBLE",     "Magnesium Factor (f)"],                                                  #17                                                   
            ["Driving_Voltage_Correction_for_0",                                 "DOUBLE",     "850V_Potential_Driving Voltage Correction for 0.850V Potential (y)"],    #18                                                                                                   
            ["Current_Output_Fron_Single_Mg_Anode_mA",                           "DOUBLE",     "Current Output Fron Single Mg Anode (mA)"],                              #19                                                                       
            ["Life_of_Magnesium_Anode_yr",                                       "DOUBLE",     "Life of Magnesium  Anode (yr)"],                                         #20                                                           
            ["Weight_lb",                                                        "DOUBLE",     "Weight (lb)"],                                                           #21                                           
            ["Capacity_of_Mg_amp_hr_lb",                                         "DOUBLE",     "Capacity of Mg (amp-hr/lb)"],                                            #22                                                           
            ["Utilization_Factor",                                               "DOUBLE",     "Utilization Factor"],                                                    #23                                                   
            ["Anode_Efficiency",                                                 "DOUBLE",     "Anode Efficiency"],                                                      #24                                               
            ["Anode_Output_A",                                                   "DOUBLE",     "Anode Output (A)"],                                                      #25                                               
            ["Number_of_Anodes_Needed",                                          "SHORT",      "Number of Anodes Needed"],                                               #26                                                       
            ["Anodes_Needed_Ft",                                                 "DOUBLE",     "Anodes Needed/Ft"],                                                      #27                                               
            ["Anodes_Installed_Anodes_Needed_Increase_in_Anode_100",             "DOUBLE",     "Anodes Installed/Anodes Needed (Increase in Anode * 100)%"],             #28                                                                                       
            ["CP_Zone_Fails_Criteria_Years",                                     "DOUBLE",     "CP Zone Fails Criteria (Years)"],                                        #29                                                                       
            ["Corrosion_Leaks_Main_and_Services_1000_Main",                      "DOUBLE",     "Corrosion Leaks (Main and Services) /1000' Main"],                       #30                                                                               
            ["Coating_Effectiveness_Degraded",                                   "DOUBLE",     "Coating Effectiveness (% Degraded)"],                                    #31                                                                   
            ["Soil_Corrosion_Rate_mil_yr",                                       "DOUBLE",     "Soil Corrosion Rate (mil/yr)"],                                          #32                                                           
            ["Distribution_Susceptability_Factor_Score",                         "DOUBLE",     "Distribution Susceptability Factor Score"],                              #33                                                                       
            ["Susceptability_Category",                                          "TEXT",      "Susceptability Category"],                                                #34                                                       
            ["Current_Required_per_Foot_A_ft",                                   "DOUBLE",     "Current Required per Foot (A/ft)"],                                      #35                                                               
            ["Distance_1_Mag_Anode_Covers_ft",                                   "DOUBLE",     "Distance 1 Mag Anode Covers (ft)"]]                                      #36 
        arcpy.management.AddFields("in_memory/Susceptibility",fields)   
        dependFields = [f[0] for f in fields]
        self.susceptibilityCost = {}
        self.susceptibilityTable = {}
        with arcpy.da.UpdateCursor("in_memory/Susceptibility",dependFields+
                                   ["Installation_Date",                         #37      
                                    "Nominal_Diameter",                          #38    
                                    "External_Coating",                          #39      
                                    "CP_Zone_Length_ft",                         #40      
                                    "Soil_Rating",                               #41      
                                    "Anodes_Installed_Max_between_CM_and_GIS",   #42
                                    "Years_Non_Compliant_850_Criteria",          #43
                                    "Corrosion_Leaks_CP_Zone",                   #44
                                    "MapCellKey"
                                    ]
                                   ) as cursor:
            for row in cursor:
                row[0]  = Score.AnodeIncrease(row[37],row[38],row[39],row[40],row[41])[8]                        #"Soil_Resistivity_ohm_cm"
                row[1]  = round(1000/row[40],5)                                                                  #"Distance_Factor_for_Corrosion_Leaks_1000"
                row[2]  = Score.AnodeIncrease(row[37],row[38],row[39],row[40],row[41])[3]                        #"Diameter_ft"
                row[3]  = 1.15                                                                                   #"k_Factor"
                row[4]  = Score.AnodeIncrease(row[37],row[38],row[39],row[40],row[41])[4]                        #idensity_mA_ft"
                row[5]  = Score.AnodeIncrease(row[37],row[38],row[39],row[40],row[41])[1]                        #ff_Coating_Effectiveness"
                row[6]  = Score.AnodeIncrease(row[37],row[38],row[39],row[40],row[41])[5]                        #fi"
                row[7]  = Score.AnodeIncrease(row[37],row[38],row[39],row[40],row[41])[6]                        #Delta_f"
                row[8]  = Score.AnodeIncrease(row[37],row[38],row[39],row[40],row[41])[7]                        #tdl"
                row[9]  = row[37].year                                                                           #"Recorded_Installation_Year"
                row[10] = Score.AnodeIncrease(row[37],row[38],row[39],row[40],row[41])[9]                        #"Estimated_Install_Year"
                row[11] = row[8]                                                                                 #"Actual_Coating_Age"
                row[12] = row[5] - row[6]                                                                        #"Change_in_Coating_Effectiveness_Change_from_Initial_until_Today"
                row[13] = 1 - row[5]                                                                             #"Coating_Effectiveness_Remaining"
                row[14] = row[13] *100                                                                           #"Coating_Effectiveness_Remaining_Percentage"
                row[15] = round(Score.AnodeIncrease(row[37],row[38],row[39],row[40],row[41])[10],5)              #"Itotal_A"
                row[16] = Score.AnodeIncrease(row[37],row[38],row[39],row[40],row[41])[11]                       #"Magnesium_Anode_Constant"
                row[17] = 1                                                                                      #"Magnesium_Factor_f"
                row[18] = 1.29                                                                                   #"Driving_Voltage_Correction_for_0"
                row[19] = Score.AnodeIncrease(row[37],row[38],row[39],row[40],row[41])[12]                       #"Current_Output_Fron_Single_Mg_Anode_mA"
                row[21] = 17                                                                                     #"Weight_lb"
                row[22] = 0.114                                                                                  #"Capacity_of_Mg_amp_hr_lb"
                row[23] = 0.85                                                                                   #"Utilization_Factor"
                row[24] = 0.5                                                                                    #"Anode_Efficiency"
                row[25] = row[19]/1000                                                                           #"Anode_Output_A"
                row[20] = round((row[21]*row[22]*row[23]*row[24])/row[25],3)                                     #"Life_of_Magnesium_Anode_yr"
                row[26] = Score.AnodeIncrease(row[37],row[38],row[39],row[40],row[41])[0]                        #"Number_of_Anodes_Needed"
                row[27] = round(row[26]/row[40],3)                                                               #"Anodes_Needed_Ft"
                if row[42] == None or row[42] == 0:             
                    row[28] = 0                                                                                  #"Anodes_Installed_Anodes_Needed_Increase_in_Anode_100"
                else:               
                    row[28] = round(row[26]/row[42],3)              
                row[29] = Score.zeroreturn(row[43])/5                                                            #"CP_Zone_Fails_Criteria_Years"
                row[30] = row[1]*Score.zeroreturn(row[44])                                                       #"Corrosion_Leaks_Main_and_Services_1000_Main"
                row[31] = row[5]                                                                                 #"Coating_Effectiveness_Degraded"
                row[32] = Score.AnodeIncrease(row[37],row[38],row[39],row[40],row[41])[2]                        #"Soil_Corrosion_Rate_mil_yr"
                row[33] =  round(row[28]+row[29]+row[30]+row[31]+row[32],3)                                      #"Distribution_Susceptability_Factor_Score"
                row[34] = Score.SusceptibilityCategory(row[33],self.susceptibilityXL)                            #"Susceptability_Category"
                row[35] = round(row[15]/row[40],6)                                                               #"Current_Required_per_Foot_A_ft"
                row[36] = round(row[25]/row[35],6)                                                               #"Distance_1_Mag_Anode_Covers_ft"
                self.susceptibilityCost[row[45]]=(row[30],Score.AnodeNeedToIncrease(row[42],row[26]))
                self.susceptibilityTable[row[45]] = (row[30],row[29],row[31],row[28],row[32],row[33],row[34])
                cursor.updateRow(row)                                          
        return

    ########################## CostCalc ##################################
    def CostCalc(self):
        arcpy.AddMessage("Extracting Cost Data")
        arcpy.management.CopyRows("in_memory/Calculation", "in_memory/Cost")
        costFields = [
            ["No_Main_Corrosion_Leaks_1000",                                 "DOUBLE",        "No. Main Corrosion Leaks/1000'"],                         #0                                  
            ["Cost_to_Repair_Expected_Main_Corrosion_Leaks_1000",            "DOUBLE",        "Cost to Repair Expected Main Corrosion Leaks (1000')"],   #1                                                      
            ["Total_Leak_Repair_Cost_Leaks_Cost",                            "DOUBLE",        "Total Leak Repair Cost (Leaks*Cost)"],                    #2                                      
            ["Anodes_to_be_Installed",                                       "DOUBLE",        "Anodes to be Installed"],                                 #3                          
            ["Cost_to_Add_Anodes_Required",                                  "DOUBLE",        "Cost to Add Anodes Required"],                            #4                              
            ["Cost_per_1000_to_Add_Anodes",                                  "DOUBLE",        "Cost per 1000' to Add Anodes"],                           #5                              
            ["Non_Anode_WO",                                                 "DOUBLE",        "Non-Anode WO"],                                           #6              
            ["Non_Anode_WO_Cost",                                            "DOUBLE",        "Non-Anode WO Cost"],                                      #7                  
            ["Cost_per_1000_Non_Anode_WO",                                   "DOUBLE",        "Cost per 1000' Non-Anode WO"],                            #8                              
            ["Annual_Survey_Cost",                                           "DOUBLE",        "Annual Survey Cost"],                                     #9                      
            ["Troubleshooting_Cost",                                         "DOUBLE",        "Troubleshooting Cost"],                                   #10                      
            ["Total_Spend_to_Maintain_CP_Per_CP_Zone",                       "DOUBLE",        "Total Spend to Maintain CP Per CP Zone"],                 #11                                          
            ["Cost_Category",                                                "TEXT",          "Cost Category"],                                          #12              
            ["Distance_Correction_Factor_1000",                              "DOUBLE",        "Distance Correction Factor (1000')"],                     #13                                      
            ["Cost_per_1000_to_Maintain",                                    "DOUBLE",        "Cost per 1000' to Maintain"],                             #14                              
            ["Cost_per_Foot_to_Maintain",                                    "DOUBLE",        "Cost per Foot to Maintain"],                              #15                          
            ["Cost_for_Pipe_Repalcement_of_CP_Zone",                         "DOUBLE",        "Cost for Pipe Repalcement of CP Zone"],                   #16                                      
            ["Maintain_Replace",                                             "TEXT",          "Maintain/ Replace"],                                      #17                  
            ["Cost_1000_to_Replace",                                         "DOUBLE",        "Cost/1000' to Replace"],                                  #18                      
            ["Total_Anodes_4A_250_rule",                                     "DOUBLE",        "Total Anodes/ 4A/250' rule"],                             #19                              
            ["Anode_cost_per_4_250_rule_limitation",                         "DOUBLE",        "Anode cost per 4/250 rule limitation"],                   #20                                      
            ["Total_Cost_to_Maintain_CP_Zone_w_Anode_Limits",                "DOUBLE",        "Total Cost to Maintain CP Zone w/ Anode Limits"]]         #21                                                  
        
        arcpy.management.AddFields("in_memory/Cost",costFields)
        self.costTable = {}
        with arcpy.da.UpdateCursor("in_memory/Cost",[f[0] for f in costFields]+[
                                    "MapCellKey",                        #22       
                                    "Corrosion_Leaks_CP_Zone",           #23                   
                                    "Work_Orders",                       #24               
                                    "Zonekeycount",                      #25               
                                    "CP_Zone_Length_ft",                 #26                             
                                    "Nominal_Diameter",                  #27
                                    "Corrosion_Leak_On_Mains"            #28  
                                    ]) as cursor:           
            for row in cursor:
                row[13] = round(1000/row[26],5)
                row[0] = row[13]*Score.zeroreturn(row[23])
                row[3] = self.susceptibilityCost[row[22]][1]
                row[1] = round(Score.costLeak(row[0],self.OCost),2)
                row[2] = round(Score.costLeak(row[28],self.OCost),2)
                row[4] = round(Score.costAnode(row[3],self.OCost),2)
                row[5] = round(row[4]*row[13],2)
                row[6] = row[24]
                row[7] = round(Score.costWO(row[24],self.OCost),2)
                row[8] = round(round(row[7],2)*row[13],2)
                row[9]  = round(Score.costTestPoint(row[25],self.OCost)[0],2)
                row[10] = round(Score.costTestPoint(row[25],self.OCost)[1],2)
                row[11] = round(row[2]+row[4]+row[7]+row[9]+row[10],2)
                row[12] = Score.CostCategory(row[11],self.costXL)
                self.costTable[row[22]] = (row[1],row[4],row[7],row[11],row[12])
                row[14] = round(row[1]+row[5]+row[8]+row[9]+row[10],2) 
                row[15] = round(row[11]/row[26],2)
                row[16] = row[26]*Score.pipeReplacementCost(row[27],self.RCost)
                
                if row[11]>row[16]:
                    row[17] = "REPLACE"
                else:
                    row[17] = "MAINTAIN"
                
                row[18] = round(row[26]*row[13]*Score.pipeReplacementCost(row[27],self.RCost),2)
                row[19] = math.ceil(row[26]/250)
                row[20] = Score.costAnode(row[19],self.OCost) 
                row[21] = row[20]+ row[2]+row[7]+row[9]+row[10]
                


                cursor.updateRow(row)
        return "in_memory/Cost"
    
    ########################## TotalEffectivenessCalc ##################################
    def TotalEffectivenessCalc(self):
        arcpy.AddMessage("Extracting TotalEffectiveness Data")
        arcpy.management.CopyFeatures("in_memory/forcalculation","in_memory/TotalEffectiveness")
        arcpy.management.AddFields("in_memory/TotalEffectiveness",
                                   [["CorrosionLeaksCPZone"                             ,"SHORT",   "Corrosion Leaks/CP Zone"],                                       #0 
                                    ["WorkOrdersCPZone"                                 ,"SHORT",   "Work Orders/CP Zone"],                                           #1 
                                    ["AnodesInstalledCPZone"                            ,"SHORT",   "Anodes Installed/CP Zone"],                                      #2 
                                    ["CoatingTypeScore"                                 ,"SHORT",   "Coating Type Score"],                                            #3 
                                    ["PipeAgeScore"                                     ,"SHORT",   "Pipe Age Score"],                                                #4 
                                    ["LevelofCPCPZone"                                  ,"SHORT",   "Level of CP/CP Zone"],                                           #5 
                                    ["CPZoneSizeFootage"                                ,"SHORT",   "CP Zone Size (Footage)"],                                        #6 
                                    ["DistributionPerformanceScore"                     ,"SHORT",   "Distribution Performance Score"],                                #7 
                                    ["PerformanceCategory"                              ,"TEXT",    "Performance Category"],                                          #8 
                                    
                                    ["DistributionTestStationMonitoredonScheduleScore"  ,"SHORT",   "Distribution Test Station Monitored on Schedule Score"],         #9 
                                    ["DistributionTestStationMeetsCriteriaScore"        ,"SHORT",   "Distribution Test Station Meets Criteria Score"],                #10
                                    ["DistributionComplianceFactor"                     ,"SHORT",   "Distribution Compliance Factor"],                                #11
                                    ["ComplianceCategory"                               ,"TEXT",    "Compliance Category"],                                           #12
                                    
                                    ["CorrosionMainLeaks1000"                           ,"DOUBLE",  "Corrosion Main Leaks/1000'"],                                    #13
                                    ["CPZoneFailsCriteriaLast5Years"                    ,"DOUBLE",  "CP Zone Fails Criteria for Last 5 Years"],                       #14
                                    ["CoatingEffectivenessDegraded"                     ,"DOUBLE",  "Coating Effectiveness (% Degraded)"],                            #15
                                    ["AnodesInstalledAnodesNeededReplacement"           ,"DOUBLE",  "Anodes Installed/Anodes Needed (Replacement %)"],                #16
                                    ["SoilCorrosionRatemilyr"                           ,"DOUBLE",  "Soil Corrosion Rate (mil/yr)"],                                  #17
                                    ["DistributionSusceptibilityFactorScore"            ,"DOUBLE",  "Distribution Susceptibility Factor Score"],                      #18
                                    ["SusceptibilityCategory"                           ,"TEXT",    "Susceptibility Category"],                                       #19
                                    
                                    ["CosttoRepairExpectedMainCorrosionLeaks"           ,"DOUBLE",   "Cost to Repair Expected Main Corrosion Leaks"],                 #20
                                    ["CosttoAddAnodesRequired"                          ,"DOUBLE",   "Cost to Add Anodes Required"],                                  #21
                                    ["NonAnodeWOCost"                                   ,"DOUBLE",   "Non-Anode WO Cost"],                                            #22
                                    ["TotalSpendtoMaintainPerCPZone"                    ,"DOUBLE",   "Total Spend to Maintain CP/CP Zone"],                           #23
                                    ["CostCategory"                                     ,"TEXT",    "Cost Category"],                                                 #24
                                    
                                    ["TotalEffectivenessRanking"                        ,"TEXT",    "Total Effectiveness Ranking"]])                                  #25                                       
        with arcpy.da.UpdateCursor("in_memory/TotalEffectiveness",[self.dcfields[0],   #0       
                                    "CorrosionLeaksCPZone",                            #1                              
                                    "WorkOrdersCPZone",                                #2                          
                                    "AnodesInstalledCPZone",                           #3                                  
                                    "CoatingTypeScore",                                #4                          
                                    "PipeAgeScore",                                    #5                      
                                    "LevelofCPCPZone",                                 #6                          
                                    "CPZoneSizeFootage",                               #7                              
                                    "DistributionPerformanceScore",                    #8                                      
                                    "PerformanceCategory",                             #9 
                                                                 
                                    "DistributionTestStationMonitoredonScheduleScore", #10                                                         
                                    "DistributionTestStationMeetsCriteriaScore",       #11                                                     
                                    "DistributionComplianceFactor",                    #12                                     
                                    "ComplianceCategory",                              #13 
                                                                
                                    "CorrosionMainLeaks1000",                          #14                                 
                                    "CPZoneFailsCriteriaLast5Years",                   #15                                         
                                    "CoatingEffectivenessDegraded",                    #16                                     
                                    "AnodesInstalledAnodesNeededReplacement",          #17                                                 
                                    "SoilCorrosionRatemilyr",                          #18                                 
                                    "DistributionSusceptibilityFactorScore",           #19                                                 
                                    "SusceptibilityCategory",                          #20                                 
                                    
                                    "CosttoRepairExpectedMainCorrosionLeaks",          #21                                                 
                                    "CosttoAddAnodesRequired",                         #22                                 
                                    "NonAnodeWOCost",                                  #23                         
                                    "TotalSpendtoMaintainPerCPZone",                   #24                                         
                                    "CostCategory",                                    #25                     
                                    "TotalEffectivenessRanking"                        #26                                 
                                ]) as cursor:
            
            for row in cursor:
                row[1]  = self.performanceTable[row[0]][0]
                row[2]  = self.performanceTable[row[0]][1]
                row[3]  = self.performanceTable[row[0]][2]
                row[4]  = self.performanceTable[row[0]][3]
                row[5]  = self.performanceTable[row[0]][4]
                row[6]  = self.performanceTable[row[0]][5]
                row[7]  = self.performanceTable[row[0]][6]
                row[8]  = self.performanceTable[row[0]][7]
                row[9]  = self.performanceTable[row[0]][8]
                row[10] = self.complianceTable[row[0]][0]
                row[11] = self.complianceTable[row[0]][1]
                row[12] = self.complianceTable[row[0]][2]
                row[13] = self.complianceTable[row[0]][3]
                row[14] = self.susceptibilityTable[row[0]][0]
                row[15] = self.susceptibilityTable[row[0]][1]
                row[16] = self.susceptibilityTable[row[0]][2]
                row[17] = self.susceptibilityTable[row[0]][3]
                row[18] = self.susceptibilityTable[row[0]][4]
                row[19] = self.susceptibilityTable[row[0]][5]
                row[20] = self.susceptibilityTable[row[0]][6]      
                row[21] = self.costTable[row[0]][0]
                row[22] = self.costTable[row[0]][1]
                row[23] = self.costTable[row[0]][2]
                row[24] = self.costTable[row[0]][3]
                row[25] = self.costTable[row[0]][4]
                overall = [row[9],row[13],row[20],row[25]]
                low = overall.count("Low")
                medium = overall.count("Medium")
                high = overall.count("High")
                row[26] = Score.OverallScore(high,medium,low) 
                cursor.updateRow(row)

# Whatif Tool
class Whatif(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "What if Tool"
        self.description = ""
        self.canRunInBackground = False
    def getParameterInfo(self):
        fileinp = arcpy.Parameter(
            displayName = "Enter Data Conditioning file",
            name = "fileinp",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")
        # fileinp.value = "DataCondition"
        hubName = arcpy.Parameter(
            displayName = "Enter HubName",
            name = "hubName",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")
        # hubName.value = "Waco"
        townName = arcpy.Parameter(
            displayName = "Enter Town Name",
            name = "townName",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")
        mapNumber = arcpy.Parameter(
            displayName = "Enter MapNumber",
            name = "mapNumber",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")
        mck = arcpy.Parameter(
            displayName = "Enter MapCellKey",
            name = "mck",
            datatype = "GPLong",
            parameterType = "Optional",
            direction = "Input")
        layerdata = arcpy.Parameter(
            displayName = "Details",
            name = "layerdata",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")
        layerdata.columns = [["GPDate","Installation Date"],
                             ["GPDouble","Nominal Diameter"],
                             ["GPString","Coating"],
                             ["GPDouble","CP Length"],
                             ["GPLong","Mains Leak"],
                             ["GPLong","Service Leak"],
                             ["GPLong","Work Order"],
                             ["GPString","Soil Rating"],
                             ["GPLong","Anode Count"],
                             ["GPLong","Test Points"],
                             ["GPLong","Years fail"],
                             ["GPLong","Years Meet"]]
        layerdata.filters[2].type = 'ValueList'
        layerdata.filters[2].list = ["Bare","Unknown","Other","Mill Wrap","Weld Wrap","Coal Tar","FBE with ARO","Tape","Fusion Bonded Epoxy","Painted"]
        layerdata.filters[7].type = 'ValueList'
        layerdata.filters[7].list = ['Extreme','High','Medium','Moderate','Low','Non-Corrosive','Default']
        instDate = arcpy.Parameter(
            displayName = "Installation Date",
            name = "instDate",
            datatype = "GPDate",
            parameterType = "Optional",
            direction = "Input")
        nominal = arcpy.Parameter(
            displayName = "Nominal Diameter",
            name = "nominal",
            datatype = "GPDouble",
            parameterType = "Optional",
            direction = "Input")
        coating = arcpy.Parameter(
            displayName = "Coating Type",
            name = "coating",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")
        coating.filter.list = ["Bare","Unknown","Other","Mill Wrap","Weld Wrap","Coal Tar","FBE with ARO","Tape","Fusion Bonded Epoxy","Painted"]
        footage = arcpy.Parameter(
            displayName = "Enter CP Length",
            name = "footage",
            datatype = "GPDouble",
            parameterType = "Optional",
            direction = "Input")
        mleak = arcpy.Parameter(
            displayName = "Mains Leak Count",
            name = "mleak",
            datatype = "GPLong",
            parameterType = "Optional",
            direction = "Input")
        leak = arcpy.Parameter(
            displayName = "Service Leak Count",
            name = "leak",
            datatype = "GPLong",
            parameterType = "Optional",
            direction = "Input")

        rating = arcpy.Parameter(
            displayName = "Soil Rating",
            name = "rating",
            datatype = "GPString",
            parameterType = "Optional",
            direction = "Input")
        rating.filter.list = ['Extreme','High','Medium','Moderate','Low','Non-Corrosive','Default']
        anode = arcpy.Parameter(
            displayName = "Anode Count",
            name = "anode",
            datatype = "GPLong",
            parameterType = "Optional",
            direction = "Input")

        ys = arcpy.Parameter(
            displayName = "Greater than 455",
            name = "ys",
            datatype = "GPBoolean",
            parameterType = "Optional",
            direction = "Input")
        ys.value="False"
        tbl = arcpy.Parameter(
            displayName = "Enter Table Path",
            name = "tbl",
            datatype = "DEWorkspace",
            parameterType = "Optional",
            direction = "Input")
        tbl.filter.list = ["GDB"]
        tblName = arcpy.Parameter(
            displayName = "Enter table name for output",
            name = "tblName",
            datatype = "GPString",
            parameterType = "Required",
            direction = "Input")
        guidelines = arcpy.Parameter(
            displayName = "Enter Guidelines Excel file",
            name = "guidelines",
            datatype = "DEFile",
            parameterType = "Optional",
            direction = "Input")
        guidelines.filter.list = ['xlsx','xls']
        
        return [fileinp,     # 0                                   
                hubName,     # 1                                   
                townName,    # 2                                   
                mapNumber,   # 3                                   
                mck,         # 4                               
                layerdata,   # 5                                   
                instDate,    # 6                                   
                nominal,     # 7                                   
                coating,     # 8                                   
                footage,     # 9                                   
                mleak,       # 10                               
                leak,        # 11                                                          
                rating,      # 12                               
                anode,       # 13                                                          
                ys,          # 14                           
                tbl,         # 15                               
                tblName,     # 16                               
                guidelines]  # 17
    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True
    def updateParameters(self, parameters):
        if parameters[0].altered:
            parameters[1].filter.list = list(set(h[0] for h in arcpy.da.SearchCursor(parameters[0].valueAsText,'HubName') if h[0] is not None))
        if parameters[1].altered:
            data = [row for row in arcpy.da.SearchCursor(parameters[0].valueAsText,["MapCellKey","HubName","TownName","MapNumber"]) if row[1]==parameters[1].valueAsText]
            df = pd.DataFrame(data,columns=["MapCellKey","HubName","TownName","MapNumber"]).fillna(" ")
            df2 = df.groupby('TownName')['MapNumber'].unique().to_dict()
            parameters[2].filter.list = list(df2.keys())
        if parameters[2].altered:
            parameters[3].filter.list = sorted(list(df2[parameters[2].valueAsText]))
            if parameters[3].altered:
                def zeroReturn(x):
                    if x!=None:
                        return x
                    else:
                        return 0
                with arcpy.da.SearchCursor(parameters[0].valueAsText, [
                    "MapCellKey","HubName","TownName","MapNumber","Installation_Date","Nominal_Diameter",
                    "External_Coating","CP_Zone_Length_ft","Corrosion_Leak_On_mains","Corrosion_Leak_On_Services","Work_Orders",
                    "Soil_Rating","Anodes_Installed_Max_between_CM_and_GIS","Zonekeycount","Years_Non_Compliant_850_Criteria","Years_Meet_1100_Criteria"
                    ]) as cursor:
                    for row in cursor:
                        if row[1] == parameters[1].value and row[2] == parameters[2].value and row[3] == parameters[3].value:
                            parameters[4].value = row[0]
                            parameters[5].values = [[row[4],zeroReturn(row[5]),row[6],zeroReturn(row[7]),zeroReturn(row[8]),zeroReturn(row[9]),zeroReturn(row[10]),row[11],zeroReturn(row[12]),zeroReturn(row[13]),zeroReturn(row[14]),zeroReturn(row[15])]]
        return
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return
    # Whatif Code
    def execute(self, parameters, messages):
        self.OCost = []
        self.RCost = []
        self.performanceXL = []
        self.complianceXL = []
        self.susceptibilityXL = []
        self.costXL = []
        if parameters[17].valueAsText != None:
            OC_DFguidelines = pd.read_excel(parameters[17].valueAsText,sheet_name='Operations Cost')
            RC_DFguidelines = pd.read_excel(parameters[17].valueAsText,sheet_name='Replacement Pipe Cost')
            PXL_DFguidelines = pd.read_excel(parameters[17].valueAsText,sheet_name='Performance')
            CoXL_DFguidelines = pd.read_excel(parameters[17].valueAsText,sheet_name='Compliance')
            SXL_DFguidelines = pd.read_excel(parameters[17].valueAsText,sheet_name='Susceptibility')
            CXL_DFguidelines = pd.read_excel(parameters[17].valueAsText,sheet_name='Cost')

            self.RCost = [(float(f[0]),float(f[1])) for f in RC_DFguidelines.values]
            self.performanceXL = [float(f[1]) for f in PXL_DFguidelines.values]
            self.complianceXL = [float(f[1]) for f in CoXL_DFguidelines.values]
            self.susceptibilityXL = [float(f[1]) for f in SXL_DFguidelines.values]
            self.costXL = [float(f[1]) for f in CXL_DFguidelines.values]
            self.OCost = [float(f[1]) for f in OC_DFguidelines.values]
        # arcpy.AddMessage(self.OCost)

        hub = parameters[1].valueAsText
        town = parameters[2].valueAsText
        map = parameters[3].valueAsText
        mapcellkey = parameters[4].value
        instDate = parameters[5].value[0][0]
        nominal = parameters[5].value[0][1]
        coating = parameters[5].value[0][2]
        footage = parameters[5].value[0][3]
        mleak = parameters[5].value[0][4]
        leak = parameters[5].value[0][5]+parameters[5].value[0][4]
        WorkOrder = parameters[5].value[0][6]
        rating = parameters[5].value[0][7]
        anode = parameters[5].value[0][8]
        testpoint = parameters[5].value[0][9]
        yc = parameters[5].value[0][10]
        ym = parameters[5].value[0][11]
        def length(le):
            dash = len(le)
            arcpy.AddMessage(dash*'-')
            arcpy.AddMessage(le)
            arcpy.AddMessage(dash*'-')
        
        if parameters[6].value != None:
            instDate = parameters[6].value
        if parameters[7].value != None:
            nominal = parameters[7].value
        if parameters[8].value != None:
            coating = parameters[8].value
        if parameters[9].value != None:
            footage = parameters[9].value
        if parameters[10].value != None:
            mleak = parameters[10].value
        if parameters[11].value != None:
            leak = parameters[11].value
        if parameters[12].value != None:
            rating = parameters[12].value
        if parameters[13].value != None:
            anode = parameters[13].value

        ## Effectiveness Calculations
        messages.addMessage(mapcellkey)
        arcpy.AddMessage('==========================')
        arcpy.AddMessage('Effectiveness Calculations')
        arcpy.AddMessage('==========================')
        
        # Performance        
        Perf_Sum = Score.CorrosionLeaksOnCPZone(leak)+Score.WorkOrders(WorkOrder)+Score.AnodesInstalledCPZone(anode)+Score.CoatingType(coating)+Score.PipeAgeScore(instDate)+Score.LevelOfCPZone(yc,ym)+Score.CPZoneSize(footage)
        arcpy.AddMessage('Performance:          '+str(Score.PerformanceCategory(Perf_Sum,self.performanceXL)))
        arcpy.AddMessage("Value:                "+str(Perf_Sum))
        
        # Compliance
        if parameters[14].value == True:
            scheduleScore = 4
        elif parameters[14].value == False:
            scheduleScore = 5
            
        ymc = int(5-yc)
        def distFactor(x):
            if x == 5:
                return 0
            else:
                return 1
        Comp_Sum = distFactor(ymc)+distFactor(scheduleScore)
        arcpy.AddMessage('Compliance:           '+str(Score.ComplianceCategory(Comp_Sum,self.complianceXL)))
        arcpy.AddMessage("Value:                "+str(Comp_Sum))
        
        # Susceptibility
        if anode == 0:
            anodescore = 0
        else:    
            anodescore = Score.AnodeIncrease(instDate,nominal,coating,footage,rating)[0]/anode
        SusSum = (anodescore)+yc/5+Score.CorrosionLeakPerCP(leak,footage)+Score.AnodeIncrease(instDate,nominal,coating,footage,rating)[1]+Score.AnodeIncrease(instDate,nominal,coating,footage,rating)[2]
        arcpy.AddMessage('Susceptibility:       '+str(Score.SusceptibilityCategory(SusSum,self.susceptibilityXL)))
        arcpy.AddMessage("Value:                "+str(SusSum))
        
        # Cost
        anodeNeededToInstall = Score.AnodeNeedToIncrease(anode,Score.AnodeIncrease(instDate,nominal,coating,footage,rating)[0])
        CostSum = Score.Price(mleak,anodeNeededToInstall,WorkOrder,testpoint,self.OCost)[0]+Score.Price(mleak,anodeNeededToInstall,WorkOrder,testpoint,self.OCost)[1]+Score.Price(mleak,anodeNeededToInstall,WorkOrder,testpoint,self.OCost)[2]+Score.Price(mleak,anodeNeededToInstall,WorkOrder,testpoint,self.OCost)[3]+Score.Price(mleak,anodeNeededToInstall,WorkOrder,testpoint,self.OCost)[4]
        arcpy.AddMessage('Cost:                 ' +str(Score.CostCategory(CostSum,self.OCost)))
        arcpy.AddMessage("Value:                "+str(CostSum))
        
        overall = [Score.PerformanceCategory(Perf_Sum,self.performanceXL),Score.ComplianceCategory(Comp_Sum,self.complianceXL),Score.SusceptibilityCategory(SusSum,self.susceptibilityXL),Score.CostCategory(CostSum,self.OCost)]
        lowCategory = overall.count("Low")
        mediumCategory = overall.count("Medium")
        highCategory = overall.count("High")
        length('TOTAL EFFECTIVENESS:  '+Score.OverallScore(lowCategory,mediumCategory,highCategory))
        
        
        arcpy.env.workspace = parameters[15].valueAsText
        if parameters[16].valueAsText not in arcpy.ListTables():
            table = arcpy.management.CreateTable("in_memory","mCalculations")                
            arcpy.management.AddFields(table,[["MapCellKey","LONG"],["HubName","TEXT"],["TownName","TEXT"],["MapNumber","TEXT"],["Installation_Date","DATE"],["Nominal_Diameter","SHORT"],["External_Coating","TEXT"],["CP_Zone_Length_ft","DOUBLE"],["Soil_Rating","TEXT"],
                                              ["Corrosion_Leak_On_mains","SHORT"],["Corrosion_Leak_On_Services","SHORT"],["Work_Orders","SHORT"],["Anodes_Installed_Max_between_CM_and_GIS","SHORT"],["Zonekeycount","SHORT"],
                                              ["Years_Non_Compliant_850_Criteria","SHORT"],["Years_Meet_1100_Criteria","SHORT"],
                                              ["PerformanceScore","SHORT"],["PerformanceCategory","TEXT"],["ComplianceScore","SHORT"],["ComplianceCategory","TEXT"],["SusceptibilityScore","DOUBLE"],["SusceptibilityCategory","TEXT"],["CostScore","DOUBLE"],["CostCategory","TEXT"],["Low","TEXT"],["Medium","TEXT"],["High","TEXT"],["TotalEffectiveness","TEXT"]])
            arcpy.management.CopyRows(table,parameters[16].valueAsText)

        cursor = arcpy.da.InsertCursor(parameters[16].valueAsText,[
            "MapCellKey","HubName","TownName","MapNumber","Corrosion_Leak_On_mains","Corrosion_Leak_On_Services","Work_Orders","Anodes_Installed_Max_between_CM_and_GIS","Zonekeycount","Nominal_Diameter","CP_Zone_Length_ft",
            "Years_Non_Compliant_850_Criteria","Years_Meet_1100_Criteria","External_Coating","Soil_Rating","Installation_Date","PerformanceScore","PerformanceCategory","ComplianceScore","ComplianceCategory","SusceptibilityScore","SusceptibilityCategory","CostScore","CostCategory","Low","Medium","High","TotalEffectiveness"])
        cursor.insertRow((
            mapcellkey,hub,town,map,mleak,leak-mleak,WorkOrder,anode,testpoint,nominal,footage,
            yc,ym,coating,rating,instDate,Perf_Sum,Score.PerformanceCategory(Perf_Sum,self.performanceXL),Comp_Sum,Score.ComplianceCategory(Comp_Sum,self.complianceXL),SusSum,Score.SusceptibilityCategory(SusSum,self.susceptibilityXL),CostSum,Score.CostCategory(CostSum,self.OCost),lowCategory,mediumCategory,highCategory,Score.OverallScore(lowCategory,mediumCategory,highCategory)))#length should be same as fields
        del cursor

class Validation(object):
    def __init__(self):
        self.label = "Validation Tool"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        cpzone = arcpy.Parameter(
            displayName = "Enter CP Zone",
            name = "cpzone",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")
        CPFields = arcpy.Parameter(
            displayName = "Enter CP Zone Fields",
            name = "CPFields",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        CPFields.parameterDependencies = [cpzone.name]
        CPFields.columns = [['String', 'MapCellKey'], ['String', 'HubName'],['String', 'TownName'],['String', 'MapNumber']]
        mains = arcpy.Parameter(
            displayName = "Enter Mains Layer",
            name = "mains",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")
        mainsList = arcpy.Parameter(
            displayName = "Enter Mains Fields",
            name = "mainsList",
            datatype = "Field",
            parameterType = "Required",
            direction = "Input")
        mainsList.columns = [['String', 'Status'], ['String', 'Material']]
        result = arcpy.Parameter(
            displayName = "Enter layer name",
            name = "result",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Output")
        return [cpzone,CPFields,mains,mainsList,result]

    def updateParameters(self, parameters):
         if parameters[0].altered:
            parameters[1].filters[0].list = [f.name for f in arcpy.ListFields(parameters[0].valueAsText)]
            parameters[1].filters[1].list = [f.name for f in arcpy.ListFields(parameters[0].valueAsText)]
            parameters[1].filters[2].list = [f.name for f in arcpy.ListFields(parameters[0].valueAsText)]
            parameters[1].filters[3].list = [f.name for f in arcpy.ListFields(parameters[0].valueAsText)]
         if parameters[2].altered:
            parameters[3].filters[0].list = [f.name for f in arcpy.ListFields(parameters[2].valueAsText)]
            parameters[3].filters[1].list = [f.name for f in arcpy.ListFields(parameters[2].valueAsText)]

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        self.cpstatus(parameters[0].valueAsText,parameters[1].value,parameters[2].valueAsText,parameters[3].value)
        splitZones = self.splitzone("in_memory/cpzone",parameters[1].value[0][0])
        with arcpy.da.UpdateCursor("in_memory/cpzone", [parameters[1].value[0][0],"CP_Status"]) as cursor:
            for row in cursor:
                if row[0] in splitZones:
                    row[1] = "Split Zone"
                cursor.updateRow(row)
        arcpy.management.CopyFeatures("in_memory/cpzone",parameters[4].valueAsText)
        return
    
    def cpstatus(self,cpl,cplList,mainsl,mainslList):
        arcpy.management.CopyFeatures(cpl,"in_memory/cpzone")
        arcpy.management.CopyFeatures(mainsl,"in_memory/mains")
        arcpy.management.AddField("in_memory/cpzone", "CP_Status", "TEXT")
        
        cpmck = cplList[0][0]
        mainsfields = mainslList[0]
        arcpy.analysis.Clip("in_memory/mains","in_memory/cpzone","in_memory/clip")
        arcpy.analysis.SpatialJoin("in_memory/clip","in_memory/cpzone","in_memory/cpmains_spatial","JOIN_ONE_TO_ONE",match_option="HAVE_THEIR_CENTER_IN")
    
        abandoned = []
        plastic = []
        with arcpy.da.SearchCursor("in_memory/cpmains_spatial", [cpmck]+mainsfields) as cursor:
            for row in cursor:
                if row[1] == "Abandoned":
                    if row[0] not in abandoned:
                        abandoned.append(row[0])
                if row[2] in ["PE","HDPE","MDPE","Plastic PE","Plastic Other","Poly (Mid-Tex)","Poly Vinyl Chloride"]:
                    if row[0] not in plastic:
                        plastic.append(row[0])
        
        new = arcpy.management.SelectLayerByLocation("in_memory/cpzone", 'INTERSECT', "in_memory/mains")
        mainsNotPresent = arcpy.SelectLayerByAttribute_management(new, "SWITCH_SELECTION")
        mainsNP = [f[0] for f in arcpy.da.SearchCursor(mainsNotPresent,cpmck)]
        
        # arcpy.AddMessage(mainsNP)
        # arcpy.AddMessage(abandoned)
        # arcpy.AddMessage(plastic)
        with arcpy.da.UpdateCursor("in_memory/cpzone", ["CP_Status",cpmck]) as cursor:
            for row in cursor:
                if row[1] in abandoned:
                    row[0] = "Abandoned"
                if row[1] in plastic:
                    row[0] = "Plastic"
                if row[1] in mainsNP:
                    row[0] = "Mains Not Present"
                cursor.updateRow(row)
        arcpy.management.DeleteField("in_memory/cpzone",cplList[0]+["CP_Status"],"KEEP_FIELDS")
        
    def splitzone(self,findSplit,mapcellkey):
        arcpy.management.CopyFeatures(findSplit,"in_memory/CP_Zone")
        arcpy.MakeFeatureLayer_management("in_memory/CP_Zone", "in_memory/layer_cp")
        arcpy.MultipartToSinglepart_management("in_memory/layer_cp","in_memory/layer_multi")
        mckCount = int(arcpy.management.GetCount("in_memory/layer_multi").getOutput(0))
        arcpy.SetProgressor("step", "Split Zones ...",0, mckCount, 1)
        with arcpy.da.SearchCursor("in_memory/layer_multi",["OBJECTID"]) as cursor:
            completed = []
            mapcellkeys = []
            for i in cursor:
                arcpy.SetProgressorLabel("Processed {0} of {1}".format(i[0],mckCount))
                if i[0] not in completed:
                    # arcpy.AddMessage(str(i[0])+" of "+str(mckCount))
                    arcpy.MakeFeatureLayer_management("in_memory/layer_multi", "in_memory/Iso_Ext_Feature")
                    new = arcpy.management.SelectLayerByAttribute("in_memory/Iso_Ext_Feature", "NEW_SELECTION", """{0} = {1}""".format(arcpy.AddFieldDelimiters("in_memory/Iso_Ext_Feature", "OBJECTID"), i[0]))
                    count = 0
                    count_new = int(arcpy.management.GetCount(new).getOutput(0))
                    while count != count_new:
                        count = arcpy.management.GetCount(new).getOutput(0)
                        new1 = arcpy.management.SelectLayerByLocation(new, "INTERSECT", "in_memory/Iso_Ext_Feature",  selection_type = "ADD_TO_SELECTION")
                        count_new = arcpy.management.GetCount(new1).getOutput(0)
                        completed = completed+[f[0] for f in arcpy.da.SearchCursor("in_memory/Iso_Ext_Feature",["OBJECTID"])]
                    for split in list(set([f[0] for f in arcpy.da.SearchCursor("in_memory/Iso_Ext_Feature",[mapcellkey])])):
                        mapcellkeys.append(split)
                arcpy.SetProgressorPosition()
            arcpy.ResetProgressor()
        # arcpy.AddMessage(mapcellkeys)
        split = []
        for f in set(mapcellkeys):
            if mapcellkeys.count(f)>1:
                # arcpy.AddMessage(f)    
                split.append(f)
        return split

# Effectiveness Calculations
class Score:
    def zeroreturn(x):
        if x == None:
            return 0
        else:
            return x

    # Performance Scores Calc
    def AnodeGreater(x,y):
        if x==None:
            return y
        elif y==None:
            return x
        elif x==None and y==None:
            return 0
        else:
            return max(x,y)
    def CorrosionLeaksOnCPZone(x):
        if x !=None:
            if x>=2 and x<=100:
                return 5
            elif x == 1:
                return 3
            elif x == 0:
                return 0
            else:
                pass   
        else:
            return 0
    def WorkOrders(x):
        if x != None:
            if x==0:
                return 0
            elif x>=1 and x<=4:
                return 1
            elif x>=5 and x<=160:
                return 2
            else:
                pass
        else:
            return 0
    def AnodesInstalledCPZone(x):
        if x!=None:
            if x==0:
                return 0
            elif x>=1 and x<=4:
                return 1
            elif x>=5 and x<=150:
                return 2
        else:
            return 0
    def CoatingType(x):
        if x!=None:
            if x=="Bare":
                return 5
            elif x=="Unknown":
                return 5
            elif x=="Other":
                return 5
            elif x=="Mill Wrap":
                return 4
            elif x=="Weld Wrap":
                return 3
            elif x=="Coal Tar":
                return 3
            elif x=="FBE with ARO":
                return 0
            elif x=="Tape":
                return 5
            elif x=="Fusion Bonded Epoxy":
                return 0
            elif x=="Painted":
                return 1
            else:
                return 0
        else:
            return 0
    def PipeAgeScore(x):
        if x!=None:
            year = x.year
            if year>=1900 and year<1960:
                return 3
            elif year>=1960 and year<1970:
                return 2
            elif year>=1970 and year<2001:
                return 1
            elif year>=2001:
                return 0
            else:
                pass   
        else:
            return 0    
    def LevelOfCPZone(mV850,mV1100):
        if mV850!=None and mV1100!=None:
            if mV850>= 1:
                return 2
            else:
                if mV1100==5:
                    return 0
                else:
                    return 1
        else:
            return 0
    def CPZoneSize(x):
        if x!=None:
            if x>=1 and x<500:
                return 3
            elif x>=500 and x<1000:
                return 2
            elif x>=1000 and x<2000:
                return 1
            elif x>=2000:
                return 1
            else:
                pass
        else:
            return 0
    def PerformanceCategory(score,*newCategory):
        if len(newCategory[0]) == 0:
            if score > 15:
                category = "High"
            elif 10 < score <=15:
                category = "Medium"
            elif score<=10:
                category = "Low"
            return category
        else:
            if score > newCategory[0][0]:
                category = "High"
            if score <= newCategory[0][0] and score >= newCategory[0][1]:
                category = "Medium"
            if score < newCategory[0][1]:
                category = "Low"
            return category
        
    # Compliance Scores Calc
    def ComplianceCategory(score,*newCategory):        
        if len(newCategory[0]) == 0:
            if score == 2:
                category = "High"
            elif score == 1:
                category = "Medium"
            elif score == 0:
                category = "Low"
            return category
        else:
            if score == newCategory[0][0]:
                category = "High"
            if score == newCategory[0][1]:
                category = "Medium"
            if score == newCategory[0][2]:
                category = "Low"
            return category
        
    # Susceptibility Scores Calc
    def AnodeIncrease(instDate,nominal,external,footage,rating):
    # calculating Nominal Dia
        dia = round(nominal/12,5)

        #calculating idensity
        if external == "Bare" or external == "Unknown":
            idensity = 2
        else:
            idensity = 0.5

        # fi and fd calculation
        if external!=None:
            if external=="FBE":
                fi,fd = 0.005,0.003
            if external=="Fusion Bonded Epoxy":
                fi,fd = 0.005,0.003
            if external=="Tape":
                fi,fd = 0.008,0.01
            if external=="FBE with ARO":
                fi,fd = 0.005,0.003
            if external=="Power Crete":
                fi,fd = 0.005,0.003
            if external=="Epoxy":
                fi,fd = 0.008,0.01
            if external=="Painted":
                fi,fd = 0.008,0.01
            if external=="Yellow Jacket":
                fi,fd = 0.001,0.0003
            if external=="3LPE / Extruded PE":
                fi,fd = 0.001,0.0003
            if external=="CT":
                fi,fd = 0.008,0.01
            if external=="Coal Tar":
                fi,fd = 0.008,0.01
            if external=="Mill Wrap":
                fi,fd = 0.008,0.01
            if external=="Weld Wrap":
                fi,fd = 0.008,0.01
            if external=="Other":
                fi,fd = 0.008,0.01
            if external=="Unknown":
                fi,fd = 0.008,0.01
            if external=="Bare":
                fi,fd = 1,0
        else:
            fi,fd = 0,0
        
        # coating Effectiveness
        presentYear = datetime.datetime.now().year
        if instDate.year == 1900 and external == "Bare":
            estdYear = 1940 
        elif instDate.year == 1900 and external != "Bare":
            estdYear = 1950
        else:
            estdYear = instDate.year
        tdl = presentYear-estdYear

        ff = fi+(fd*tdl)

        if ff>0.4:
            mg = 150000
        else:
            mg = 120000
        
        if rating!=None:
            if rating=="Extreme":
                resistivity,rating = 1000,5
            if rating=="High":
                resistivity,rating = 3000,5
            if rating=="Medium":
                resistivity,rating = 4000,1.57
            if rating=="Moderate":
                resistivity,rating = 7500,0.39
            if rating=="Low":
                resistivity,rating = 10000,0.098
            if rating=="Non-Corrosive":
                resistivity,rating = 20000,0.001
            if rating=="Default":
                resistivity,rating = 3000,5
        else:
            resistivity,rating = 0,0
        iTotal = (3.14159*idensity*dia*footage*ff)/1000
        currentOutput = (mg*1*1.29)/resistivity
        anodeOutput = currentOutput/1000
        anodeNumNeed = math.ceil(iTotal/anodeOutput)
        return anodeNumNeed,ff,rating,dia,idensity,fi,fd,tdl,resistivity,estdYear,iTotal,mg,currentOutput
   
    def CorrosionLeakPerCP(leak,cp):
        if leak!=None:
            cpf = 1000/cp
            return (leak*cpf)
        else:
            return 0

    def AnodeNeedToIncrease(installed,needed):
        if installed != None and needed!=None:
            if installed < needed:
                return needed-installed
            elif installed >= needed:
                return 0
        elif installed == None and needed ==None:
            return 0
        elif installed ==None:
            return needed
        elif needed == None:
            return 0
        else:
            return 0   
    def SusceptibilityCategory(score,*newCategory):
        if len(newCategory[0]) == 0:
            if score > 7.0:    
                category = "High"
            elif score >=1.0 and score <= 7.0:    
                category = "Medium"
            elif score < 1.0:    
                category = "Low"
            return category 
        else:
            if score > newCategory[0][0]:
                category = "High"
            if score <= newCategory[0][0] and score >= newCategory[0][1]:
                category = "Medium"
            if score < newCategory[0][1]:
                category = "Low"
            return category
        
    # Cost Scores Calc
    def Price(leakMains,anodeNeeded,workOrder,testPoint,*newval):
        if leakMains!= None:
            if len(newval[0]) == 0:
                leakRepair = leakMains* 3000.00
            else:
                leakRepair = leakMains* newval[0][0]
                 
        else:
            leakRepair = 0

        if anodeNeeded!= None:
            if len(newval[0]) == 0:
                cost = anodeNeeded * 3000.00 
            else:
                cost = anodeNeeded * newval[0][1]
                
        else:
            cost = 0

        if workOrder!= None:
            if len(newval[0]) == 0:
                anode = workOrder*72.11*8
            else:
                anode = workOrder*newval[0][2]
                
        else:
            anode = 0

        if testPoint != None:
            if len(newval[0]) == 0:
                survey = testPoint *72.11*0.4  
                trouble = testPoint * 72.11*2.4
            else: 
                survey = testPoint * newval[0][3]
                trouble = testPoint * newval[0][4]
        else:
            survey = 0
            trouble = 0
        return leakRepair,cost,anode,survey,trouble 
    
    def costLeak(leakMains,*newCost):
        if leakMains!= None:
            if len(newCost[0]) == 0:
                return leakMains * 3000.00 
            else:
                return leakMains * newCost[0][0] 
                
        else:
            return 0
    def costAnode(anodeNeeded,*newCost):
        if anodeNeeded!= None:
            if len(newCost[0]) == 0:
                return anodeNeeded * 3000.00 
            else:
                return anodeNeeded * newCost[0][1] 
                
        else:
            return 0
    def costWO(workOrder,*newCost):
        if workOrder!= None:
            if len(newCost[0]) == 0:
                return workOrder*72.11*8
            else:
                return workOrder*newCost[0][2]
                
        else:
            return 0

    def costTestPoint(testPoint,*newCost):
        if testPoint != None:
            if len(newCost[0]) == 0:
                survey = testPoint *72.11*0.4  
                trouble = testPoint * 72.11*2.4 
            else:
                survey = testPoint * newCost[0][3]
                trouble = testPoint * newCost[0][4]
            
            return survey,trouble
        else:
            survey = 0
            trouble = 0
            return survey,trouble

    def pipeReplacementCost(dia,*newCost):
        if len(newCost[0]) == 0:
            if dia > 0 and dia <=3:
                costPerFoot = 48
            if dia > 3 and dia <=4:
                costPerFoot = 66
            if dia > 4 and dia <=6:
                costPerFoot = 101
            if dia > 6 and dia <=10:
                costPerFoot = 111
            if dia > 10:
                costPerFoot = 146        
        else:
            for f in newCost[0]:
                if f[0] == dia:
                    costPerFoot = f[1]
        # if dia == 1:
        #     diameter = 48 
        # if dia == 1.25:
        #     diameter = 48 
        # if dia == 2:
        #     diameter = 48 
        # if dia == 2.5:
        #     diameter = 48 
        # if dia == 3:
        #     diameter = 48 
        # if dia == 4:
        #     diameter = 66 
        # if dia == 5:
        #     diameter = 66 
        # if dia == 6:
        #     diameter = 101 
        # if dia == 8:
        #     diameter = 111 
        # if dia == 10:
        #     diameter = 111 
        # if dia == 12:
        #     diameter = 146 
        # if dia == 16:
        #     diameter = 146 
        # if dia == 18:
        #     diameter = 146 
        # if dia == 20:
        #     diameter = 146 
        return costPerFoot

    def CostCategory(score,*newCategory):
        if len(newCategory[0]) == 0:
            score = round(score,0)
            if score > 100000:
                category = "High"
            elif score <= 100000 and score >= 20000:
                category = "Medium"
            elif score < 20000:
                category = "Low"
            return category
        else:
            high = newCategory[0][0]
            low = newCategory[0][1]
            if score > high:
                category = "High"
            if score <= high and score >= low:
                category = "Medium"
            if score < low:
                category = "Low"
            return category
            
    
    # Overall Score Scores Calc
    def OverallScore(low,high, medium):
        if high ==4 and medium ==0 and low==0:
            return "High"
        if high ==3 and medium ==1 and low==0:
            return "High"
        if high ==3 and medium ==0 and low==1:
            return "High"
        if high ==2 and medium ==2 and low==0:
            return "High"
        if high ==2 and medium ==0 and low==2:
            return "Medium"
        if high ==2 and medium ==1 and low==1:
            return "Medium"
        if high ==1 and medium ==3 and low==0:
            return "Medium"
        if high ==1 and medium ==0 and low==3:
            return "Medium"
        if high ==1 and medium ==2 and low==1:
            return "Medium"
        if high ==1 and medium ==1 and low==2:
            return "Medium"
        if high ==0 and medium ==4 and low==0:
            return "High"
        if high ==0 and medium ==3 and low==1:
            return "Medium"
        if high ==0 and medium ==2 and low==2:
            return "Low"
        if high ==0 and medium ==1 and low==3:
            return "Low"
        if high ==0 and medium ==0 and low==4:
            return "Low"
        