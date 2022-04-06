#!/usr/bin/env python3
"""
@author: Benjamin Menetrier
@description: plotting facility for FV3
"""

# (C) Copyright 2021 UCAR
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.

import os
import argparse
import sys
import time
from netCDF4 import Dataset
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.cm as cm
import numpy as np
import copy
import subprocess
import cartopy.crs as ccrs

# -----------------------------------------------------------------------------

# Initial time
initial_time = time.perf_counter()

# -----------------------------------------------------------------------------

# Environment variables

# FV3_GRID_DIR: directory with FV3 grid files for each resolution ("fv3grid_cNNNN.nc")
gridfiledir = os.environ.get("FV3_GRID_DIR", os.path.dirname(os.path.realpath(__file__)) + "/fv3grid")

# Hard-coded parameters

# Number of tiles
ntile = 6

# Projection
projection = ccrs.Robinson()

# -----------------------------------------------------------------------------

# Parser
parser = argparse.ArgumentParser()

# GEOS / GFS input file
parser.add_argument("--geos", dest="geos", action="store_true", help="GEOS input file")
parser.add_argument("--gfs", dest="gfs", action="store_true", help="GFS input file")

# File path
parser.add_argument("--filepath", "-f", help="File path")

# Base file path to compute a difference (optional)
parser.add_argument("--basefilepath", "-bf", help="Base file path to compute a difference (optional)")

# Variable
parser.add_argument("--variable", "-v", help="Variable")

# Level
parser.add_argument("--level", "-l", type=int, help="Level")

# Averaging size (optional, default=1)
parser.add_argument("--average", "-a", type=int, nargs="?", help="Averaging size (optional, default=1)", default=1)

# Value threshold (optional, default=0.0)
parser.add_argument("--threshold", "-th", type=float, nargs="?", help="Value threshold (optional, default=0.0)", default=0.0)

# Color map (optional, default=jet or coolwarm)
parser.add_argument("--colormap", "-cm", type=str, nargs="?", help="Color map (optional, default=jet or coolwarm)")

# Centered color map
parser.add_argument("--centered", dest="centered", action="store_true", help="Centered color map")

# Cross representation (a lot faster)
parser.add_argument("--cross", dest="cross", action="store_true", help="Cross representation")

# Output file path
parser.add_argument("--output", "-o", help="Output file path")

# -----------------------------------------------------------------------------

# Parse arguments
args = parser.parse_args()

# Set default string values
if args.colormap is None:
    if args.centered:
        args.colormap = "coolwarm"
    else:
        args.colormap = "jet"

# Print arguments
print("Parameters:")
print(" - gridfiledir: " + gridfiledir)
for arg in vars(args):
    if not arg is None:
        print(" - " + arg + ": " + str(getattr(args, arg)))


# Check arguments
if (not (args.geos or args.gfs)):
    print("ERROR: --geos or --gfs required")
    sys.exit(1)

# -----------------------------------------------------------------------------

# Lon/lat test
lon_test = False
lat_test = False

if lon_test and lat_test:
    print("ERROR: lon_test and lat_test are mutually exclusive")
    sys.exit(1)

if (lon_test or lat_test) and args.gfs:
    print("ERROR: lon_test and lat_test are only available with GFS")
    sys.exit(1)

# -----------------------------------------------------------------------------

if args.geos:
    # Check file extension
    if not args.filepath.endswith(".nc4"):
        print("   Error: filepath extension should be .nc4")
        sys.exit(1)

    # Open data file
    fdata = Dataset(args.filepath, "r", format="NETCDF4")

    if lon_test:
        # Read lon
        fld = fdata["lons"][:,:,:]
    elif lat_test:
        # Read lat
        fld = fdata["lats"][:,:,:]
    else:
        # Read field
        fld = fdata[args.variable][0,args.level-1,:,:,:]

    if not args.basefilepath is None:
        # Check base file extension
        if not args.basefilepath.endswith(".nc4"):
            print("   Error: basefilepath extension should be .nc4")
            sys.exit(1)

        # Open data file
        fdata = Dataset(args.basefilepath, "r", format="NETCDF4")

        # Read field
        basefld = fdata[args.variable][0,args.level-1,:,:,:]

        # Compute increment
        fld = fld - basefld

    # Get shape
    shp = np.shape(fld)
    ny = shp[1]
    nx = shp[2]
else:
    # Check file extension
    if not args.filepath.endswith(".nc"):
        print("   Error: filepath extension should be .nc")
        sys.exit(1)

    for itile in range(0, ntile):
        # Open data file
        filename = args.filepath.replace(".nc", ".tile" + str(itile+1) + ".nc")
        fdata = Dataset(filename, "r", format="NETCDF4")

        # Read field
        fld_tmp = fdata[args.variable][0,args.level-1,:,:]

        if itile == 0:
            # Get shape
            shp = np.shape(fld_tmp)
            ny = shp[0]
            nx = shp[1]

            # Initialize field
            fld = np.zeros((ntile, ny, nx))

        # Copy field
        fld[itile,:,:] = fld_tmp

    if not args.basefilepath is None:
        # Check base file extension
        if not args.basefilepath.endswith(".nc"):
            print("   Error: basefilepath extension should be .nc")
            sys.exit(1)

        for itile in range(0, ntile):
            # Open data file
            filename = args.basefilepath.replace(".nc", ".tile" + str(itile+1) + ".nc")
            fdata = Dataset(filename, "r", format="NETCDF4")

            # Read field
            fld_tmp = fdata[args.variable][0,args.level-1,:,:]

            # Copy field
            fld[itile,:,:] = fld[itile,:,:] - fld_tmp

# Open grid file
fgrid = Dataset(gridfiledir + "/fv3grid_c" + str(nx).zfill(4) + ".nc4", "r", format="NETCDF4")

# Read grid vertices lons/lats
vlons = np.degrees(fgrid["vlons"][:,:,:])
vlats = np.degrees(fgrid["vlats"][:,:,:])

# Compute min/max
if args.centered:
    vmax = np.max(np.abs(fld))
    vmin = -vmax
else:
    vmin = np.min(fld)
    vmax = np.max(fld)
norm = plt.Normalize(vmin=vmin, vmax=vmax)

# Compute averaging norm
normavg = 1.0/args.average**2

# Initialize figure
if args.cross:
   fig,ax = plt.subplots(figsize=(8,8))
else:
   fig,ax = plt.subplots(figsize=(8,8),subplot_kw=dict(projection=projection))
   ax.set_global()
   ax.coastlines()
   ax.gridlines()

# Colormap
cmap = copy.copy(cm.get_cmap(args.colormap))
cmap.set_bad('gray', 1)

# Figure title
if args.average > 1:
    plt.title(args.variable + " at level " + str(args.level) + " - C" + str(nx) + " - Avg. " + str(args.average))
else:
    plt.title(args.variable + " at level " + str(args.level) + " - C" + str(nx))

if args.cross:
    nxc = 3*nx
    nyc = 4*ny
    fld_cross =  np.zeros((nxc,nyc))
    fld_cross[:,:] = np.inf
    fld_cross[1*nx:2*nx,1*ny:2*ny] = fld[0,:,:]
    fld_cross[1*nx:2*nx,2*ny:3*ny] = fld[1,:,:]
    fld_cross[2*nx:3*nx,1*ny:2*ny] = np.rot90(fld[2,:,:],3)
    fld_cross[1*nx:2*nx,3*ny:4*ny] = np.rot90(fld[3,:,:])
    fld_cross[1*nx:2*nx,0*ny:1*ny] = np.rot90(fld[4,:,:])
    fld_cross[0*nx:1*nx,1*ny:2*ny] = fld[5,:,:]
    ax.pcolormesh(fld_cross, cmap=cmap, vmin=vmin, vmax=vmax);
else:
    # Loop over tiles
    for itile in range(0, ntile):
        # Loop over polygons
        for iy in range(0, ny, args.average):
            for ix in range(0, nx, args.average):
                # Average value
                value = 0.0
                for iya in range(0, args.average):
                    for ixa in range(0, args.average):
                        value += fld[itile,iy+ixa,ix+ixa]
                value = value*normavg

                if abs(value) >= args.threshold:
                    # Polygon coordinates      
                    xy = [[vlons[itile,iy+0,ix+0], vlats[itile,iy+0,ix+0]],
                          [vlons[itile,iy+0,ix+args.average], vlats[itile,iy+0,ix+args.average]],
                          [vlons[itile,iy+args.average,ix+args.average], vlats[itile,iy+args.average,ix+args.average]],
                          [vlons[itile,iy+args.average,ix+0], vlats[itile,iy+args.average,ix+0]]]

                    # Add polygon
                    ax.add_patch(mpatches.Polygon(xy=xy, closed=True, facecolor=cmap(norm(value)),transform=ccrs.Geodetic()))

# Set colorbar
sm = cm.ScalarMappable(cmap=args.colormap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
sm.set_array([])
plt.colorbar(sm, orientation="horizontal", pad=0.06)

# Save and close figure
plt.savefig(args.output + ".jpg", format="jpg", dpi=300)
plt.close()

# Trim figure with mogrify if available
info = subprocess.getstatusoutput('mogrify')
if info[0] == 0:
    subprocess.run(["mogrify", "-trim", args.output + ".jpg"])

# Print plot path
print(" -> plot produced: " + args.output + ".jpg")

# -----------------------------------------------------------------------------

# Final time
final_time = time.perf_counter()

# Print timing
print(f"raster.py executed in {final_time - initial_time:0.4f} seconds")
