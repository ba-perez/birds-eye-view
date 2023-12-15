#the following python modules need to be installed:
import ee

#authenticate the GEE account and initialise the API
ee.Authenticate()
ee.Initialize()

#######################################
############## PARAMETERS #############
#######################################

#specify the path to your GEE asset containing the studied fields
field_asset = ee.FeatureCollection('projects/ee-your_account/assets/asset_name')

#set an area of interest to filter satellite images by. Only images overlapping with the AoI will be selected.
#this script worked with coordinates representing polygon vertices
area_of_interest = [
    [12.24781567858654, 48.63364077609223],
    [12.24781567858654, 48.748023697709286],
    [12.808848918234043, 48.748023697709286],
    [12.808848918234043, 48.63364077609223],
    [12.24781567858654, 48.63364077609223]
    ]
AOI = ee.Geometry.Polygon(area_of_interest)

#define a date range to filter Landsat-7's image collection by
START_DATE = '2017-03-01'
END_DATE = '2023-07-31'

#define a calendar range to filter Landsat-7's image collection by
#within the date range, only images within the specified months will be selected
#this is relevant when the date range covers more than one year
MONTH_FILTER = ee.Filter.calendarRange(3, 7, 'month')

#number of pixels to buffer the identified clouds and cloud shadows by (optional)
#for Sentinel-2 NDVI calculations, 1 pixel = 10m
BUFFER = 7

#further masking parameters specified by Braaten (2022)
CLD_PRB_THRESH = 65
NIR_DRK_THRESH = 0.15
CLD_PRJ_DIST = 1

#######################################
################ MASKING ##############
#######################################

#Parameters for exporting the time series as  CSV file to a Google Drive folder
fields = field_asset #specify asset with fields for median calculation and export
fieldIdColumn = 'fid' #change 'fid' to the name of the field ID column in the shapefile being processed
description = 'S2_2017_2023' #define a name for the CSV
folder_name = 'NDVI_timeseries' #specify the destination folder. The folder needs to exist in the Google Drive linked to the GEE account.

#function to filter image collection
def get_s2_sr_cld_col(aoi, start_date, end_date):
    s2_sr_col = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(MONTH_FILTER)
        )

    s2_cloudless_col = (ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(MONTH_FILTER))

    return ee.ImageCollection(ee.Join.saveFirst('s2cloudless').apply(**{
        'primary': s2_sr_col,
        'secondary': s2_cloudless_col,
        'condition': ee.Filter.equals(**{
            'leftField': 'system:index',
            'rightField': 'system:index'
        })
    }))

#apply function
filtered_IC = get_s2_sr_cld_col(AOI, START_DATE, END_DATE)

#cloud masking function
def add_cloud_bands(img):
    cld_prb = ee.Image(img.get('s2cloudless')).select('probability')
    is_cloud = cld_prb.gt(CLD_PRB_THRESH).rename('clouds')
    return img.addBands(ee.Image([cld_prb, is_cloud]))

#shadow masking function
def add_shadow_bands(img):
    not_water = img.select('SCL').neq(6)
    SR_BAND_SCALE = 1e4
    dark_pixels = img.select('B8').lt(NIR_DRK_THRESH*SR_BAND_SCALE).multiply(not_water).rename('dark_pixels')
    shadow_azimuth = ee.Number(90).subtract(ee.Number(img.get('MEAN_SOLAR_AZIMUTH_ANGLE')));
    cld_proj = (img.select('clouds').directionalDistanceTransform(shadow_azimuth, CLD_PRJ_DIST*10)
        .reproject(**{'crs': img.select(0).projection(), 'scale': 100})
        .select('distance')
        .mask()
        .rename('cloud_transform'))
    shadows = cld_proj.multiply(dark_pixels).rename('shadows')
    return img.addBands(ee.Image([dark_pixels, cld_proj, shadows]))

#aggregate cloud and cloud shadow masking functions
def add_cld_shdw_mask(img):
    img_cloud = add_cloud_bands(img)
    img_cloud_shadow = add_shadow_bands(img_cloud)
    is_cld_shdw = img_cloud_shadow.select('clouds').add(img_cloud_shadow.select('shadows')).gt(0)
    is_cld_shdw = (is_cld_shdw.focalMin(2).focalMax(BUFFER)
        .reproject(**{'crs': img.select([0]).projection(), 'scale': 10})
        .rename('cloudmask'))
    return img_cloud_shadow.addBands(is_cld_shdw)

#identify cloud and shadow and add classification as bands
#clip to AoI
IC_withMaskBands = filtered_IC.map(add_cld_shdw_mask).map(lambda image: image.clip(AOI))

#apply cloud and shadow masks
def maskCloudsAndShadows(image):
    cloudmask = image.select('cloudmask')
    maskedImage = image.updateMask(cloudmask.eq(0))
    return maskedImage

#mask out clouds and shadows
masked_IC = IC_withMaskBands.map(maskCloudsAndShadows)

#######################################
################# NDVI ################
#######################################

#calculate NDVI
#resulting images will only have NDVI bands after this step
IC_withIndices = masked_IC.scaleAndOffset().spectralIndices(["NDVI"])

#######################################
################## CSV ################
#######################################

#function to export NDVI time series as CSV to Google Drive folder
def exportTimeSeriesToCSV(description, s2CloudMasked, fieldIdColumn):
    region_list = fields.toList(fields.size())
  
    def exportFunction(ele):
        geometry = ee.Feature(ele).geometry()
        sen2_masked_export = s2CloudMasked.filterBounds(geometry)
    
        def getData(e):
            image = ee.Image(e)
            date = ee.Date(image.get("system:time_start")).format().slice(0, 10)
      
            region = image.reduceRegion(ee.Reducer.median(), geometry)
            
            ft = ee.Feature(None, {
                'date': date,
                'NDVI': region.get('NDVI'),
                'field_id': ee.Feature(ele).get(fieldIdColumn)
            })
      
            return ft
    
        return sen2_masked_export.toList(sen2_masked_export.size()).map(getData).flatten()
  
    forExport = region_list.map(exportFunction)
    task = ee.batch.Export.table.toDrive(
        collection=ee.FeatureCollection(forExport.flatten()),
        description=description,
        selectors=['date, NDVI, field_id'],
        folder=folder_name
    )
    task.start()

#start export
exportTimeSeriesToCSV(description, IC_withIndices, fieldIdColumn)
