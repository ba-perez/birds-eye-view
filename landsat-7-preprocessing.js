///////////////////////////////////////
/////////// ** VARIABLES ** ///////////
///////////////////////////////////////

//define a date range to filter Landsat-7's image collection by

var startDate = '2017-03-01'; 
var endDate = '2023-07-31';

//define a calendar range to filter Landsat-7's image collection by
//within the date range, only images within the specified months will be selected
//this is relevant when the date range covers more than one year
var startMonth = 3;
var endMonth = 7;

//define a region to filter Landsat-7's image collection by
//this code works with a shapefile uploaded to GEE as an asset
//the shapefile should contain each field as a separate feature
var region = region_asset;

//load the Landsat-7 image collection, filter by specifications
var l7_original = ee.ImageCollection("LANDSAT/LE07/C02/T1_L2")
                     .filterDate(startDate, endDate)
                     .filter(ee.Filter.calendarRange(startMonth, endMonth, 'month'))
                     .filterBounds(region);

Map.centerObject(region, 15); //center visualisation on defined region

///////////////////////////////////////
////////// ** CLOUD MASK ** ///////////
///////////////////////////////////////

//cloud masking function
function maskL7sr(image) {
  var qaMask = image.select('QA_PIXEL').bitwiseAnd(parseInt('11111', 2)).eq(0);
  var saturationMask = image.select('QA_RADSAT').eq(0);
  var opticalBands = image.select('SR_B.').multiply(0.0000275).add(-0.2);
  var thermalBands = image.select('ST_B6').multiply(0.00341802).add(149.0).subtract(273.15);
  return image.addBands(opticalBands, [], true)
      .addBands(thermalBands, [], true)
      .updateMask(qaMask)
      .updateMask(saturationMask)
}

//apply cloud mask
var l7_masked = l7_original.map(maskL7sr);

///////////////////////////////////////
////////// ** RESAMPLING ** ///////////
///////////////////////////////////////

//select bands for resampling
var l7_masked = ee.ImageCollection(l7_masked)
  .select(
    ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7']
  )

//define new resolution as reference
//sentinel-2 bands with 10m resolution are used
var reference_S2_10m = ee.ImageCollection("COPERNICUS/S2_SR")
  .filterDate(startDate, endDate)
  .filterBounds(region)
  .sort('CLOUDY_PIXEL_PERCENTAGE')
  .select(
    ['B4', 'B3', 'B2', 'B8']
  );

//resampling function using bicubic interpolation
var resampleLandsat = function(image) {
  var resampled = image
    .resample('bicubic')
    .reproject({
      crs: reference_S2_10m.first().projection().crs(),
      scale: reference_S2_10m.first().projection().nominalScale() //scale 10
    });
  return resampled.copyProperties(image, image.propertyNames());
};

//apply resampling
var l7_masked = l7_masked.map(resampleLandsat);

///////////////////////////////////////
//////////// ** ADD NDVI ** ///////////
///////////////////////////////////////

//NDVI is calculated using the code by Monteiro et al. (2023):

/*
spectral module: https://github.com/davemlz/spectral
Awesome Spectral Indices for GEE: https://github.com/davemlz/awesome-ee-spectral-indices
*/

//require the module from the open repository
var spectral = require("users/dmlmont/spectral:spectral");

//define region for use in the module
var pivot = region;

//check bands required for the index (optional)
//print('Required bands for NDVI', spectral.indices.NDVI.bands);

//define dataset to get the scale and offset values from
var dataset = "LANDSAT/LE07/C02/T1_L2";

//module function to add index to image collection
function addIndices(img) {
  img = spectral.scale(img,dataset); 
  img = spectral.offset(img,dataset);
  
  //required bands to calculate desired index
  var parameters = {
    "N": img.select("SR_B4"),
    "R": img.select("SR_B3"),
  };

  //compute NDVI
  return spectral.computeIndex(
    img,["NDVI"],
    parameters);
  
}

//apply function to dataset
var l7_masked = l7_masked.map(addIndices);

///////////////////////////////////////
////////////// ** CSV ** //////////////
///////////////////////////////////////

//function to calculate NDVI medians for each field in shape file
//and define information to be added to the CSV file
var region_list = region.toList(region.size());
var forExport = region_list.map(function (ele) {
  var l7_masked_export = l7_masked.filter(ee.Filter.bounds(ee.Feature(ele).geometry()));
  var getData = l7_masked_export.toList(l7_masked_export.size()).map(function (e) {
    var date = ee.Date(ee.Image(e).get("system:time_start")).format().slice(0,10);
    var NDVI = ee.Image(e).reduceRegion(ee.Reducer.median(), ee.Feature(ele).geometry()).get('NDVI');
    var ft = ee.Feature(null, {'date': date, 
                               'NDVI': NDVI,
                               'field_id': ee.Feature(ele).get('fid') //change 'fid' to the name of the field ID column in the shapefile being processed
    });
    return ft;
  });
  return getData;
});

//export NDVI time series as CSV to a Google Drive folder
Export.table.toDrive({
    collection: ee.FeatureCollection(forExport.flatten()),
    selectors: 'date, NDVI, field_id',
    description: 'L7_2017_2023', //define a name for the CSV
    folder: 'NDVI_timeseries' //specify the destination folder. The folder needs to exist in the Google Drive linked to the GEE account.
});
