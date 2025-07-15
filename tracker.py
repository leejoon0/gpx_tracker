import gpxpy
import matplotlib.pyplot as plt
import datetime
from geopy import distance
from math import sqrt, floor
import numpy as np
import pandas as pd
import chart_studio.plotly as py
import plotly.graph_objs as go
import haversine

gpx_file = open('activity_11926302489.gpx', 'r', encoding='utf-8')
gpx = gpxpy.parse(gpx_file)

data = gpx.tracks[0].segments[0].points

start = data[0]
finish = data[-1]

df = pd.DataFrame(columns=['lon', 'lat', 'alt', 'time'])
for point in data:
    df = pd.concat([df, pd.DataFrame([{'lon': point.longitude, 'lat' : point.latitude, 'alt' : point.elevation, 'time' : point.time}])], ignore_index=True)

#print(df)

plt.plot(df['lon'], df['lat'])

# df['time'] = df['time'].dt.tz_localize(None)
# plt.plot(df['time'], df['alt'])
# 
# Ulleung = folium.Map(location=[37.4, 131.3], zoom_start=9)

plt.show()