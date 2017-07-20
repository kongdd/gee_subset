#!/usr/bin/env python

# Google Earth Engine (GEE) Subsets
# 
# Easy subsetting of remote sensing
# time series for processing external
# to GEE.
# 
# This in parts replaces the ORNL DAAC
# MODIS subsets, but extends it to higher
# resolution date such as Landsat and
# Sentinel. It should also work on all
# other gridded products using the same
# product / band syntax.

# load required libraries
import os, argparse
from datetime import datetime
import pandas as pd
import ee

# parse arguments in a beautiful way
# includes automatic help generation
def getArgs():

   # setup parser
   parser = argparse.ArgumentParser(
    description = '''Google Earth Engine subsets script: 
                    Allows for the extraction of remote sensing product
                    time series for most of the data available on
                    Google Earth Engine. Locations need to be specied as
                    either a comma delimited file or an explicit latitude
                    and longitude using command line arguments.''',
    epilog = '''post bug reports to the github repository''')
   parser.add_argument('-p',
                       '--product',
                       help = 'remote sensing product available in GEE',
                       required = True)
                       
   parser.add_argument('-b',
                       '--band',
                       help = 'band name for the requested product',
                       nargs = "+",
                       required = True)
                       
   parser.add_argument('-s',
                       '--start',
                       help = 'start date of the time series (yyyy-mm-dd)',
                       default = "2013-01-01")
                       
   parser.add_argument('-e',
                       '--end',
                       help = 'end date of the time series (yyyy-mm-dd)',
                       default = "2014-12-31")
                       
   parser.add_argument('-r',
                       '--radius',
                       help = 'km east west north south',
                       default = "0")

   parser.add_argument('-sc',
                       '--scale',
                       help = '''scale in meter, match the native resolution of
                       the data of interest otherwise mismatches in scale will result in
                       high pixel counts and a system error''',
                       default = "30")

   parser.add_argument('-loc',
                       '--location',
                       nargs = 2,
                       help = '''geographic location as latitude longitude
                       provided as -loc latitude longitude''',
                       default = 0)

   parser.add_argument('-f',
                       '--file',
                       help = '''path to file with geographic locations
                        as provided in a csv file''',
                       default = 0)
                       
   parser.add_argument('-d',
                       '--directory',
                       help = '''directory / path where to write output when not
                       provided this defaults to output to the console''',
                       default = 0)                       

   # put arguments in dictionary with
   # keys being the argument names given above
   return parser.parse_args()

# MAIN
if __name__ == "__main__":

   # parse arguments
   args = getArgs()
   
   # read in locations if they exist,
   # overrides the location argument
   if args.file:
      if os.path.isfile(args.file):
        if args.loc:
            print("not a valid location file, check path") 
        else:
            locations = ('site',) + tuple(args.location)
      else:
          locations = pd.read_csv(args.file)
   
   # fix the geometry when there is a radius
   # 0.01 degree = 1.1132 km on equator
   # or 0.008983 degrees per km (approximate)
   if args.radius > 0 :
    radius = float(args.radius) * 0.008983   	 
   
   # initialize GEE session
   # requires a valid authentication token
   # to be present on the system
   ee.Initialize()
   
   # now loop over all locations and grab the
   # data for all locations as specified in the
   # csv file or the single location as specified
   # by a lat/lon tuple
   for loc in locations.itertuples():
      
      # some feedback
      print("processing: " + loc[1]) 
    
      # setup the geometry, based upon point locations as specified
      # in the locations file or provided by a latitude or longitude
      # on the command line / when a radius is provided pad the location
      # so it becomes a rectangle (report all values raw in a tidy
      # matrix)
      if args.radius:
        geometry = ee.Geometry.Rectangle(
          [loc[3] - radius, loc[2] - radius,
          loc[3] + radius, loc[2] + radius])
      else:
        geometry = ee.Geometry.Point([loc[3], loc[2]])

      # define the collection from which to sample
      col = ee.ImageCollection(args.product).select(tuple(args.band)).filterDate(args.start, args.end)
      
      # region values as generated by getRegion
      region = col.getRegion(geometry, int(args.scale)).getInfo()
      
      # stuff the values in a dataframe for convenience      
      df = pd.DataFrame.from_records(region[1:len(region)])
      
      # use the first list item as column names
      df.columns = region[0]
      
      # drop id column (little value / overhead)
      df.drop('id', axis=1, inplace=True)
      
      # divide the time field by 1000 as in milliseconds
      # while datetime takes seconds to convert unix time
      # to dates
      df.time = df.time / 1000
      df['time'] = pd.to_datetime(df['time'], unit='s')
      df.rename(columns={'time': 'date'}, inplace=True)
      
      # add the product name and latitude, longitude as a column
      # just to make sense of the returned data after the fact
      df['product'] = pd.Series(args.product, index = df.index)
      
      # print results to console if no output
      # directory is provided, else write to
      # file
      if args.directory:
       df.to_csv(args.directory + loc[1] + "_gee_subset.csv")
      else:
       print(df)