import re
import base64
import gpxpy
import pandas as pd
import folium
import requests
from urllib import request
from datetime import datetime
from io import BytesIO
import os
from matplotlib.figure import Figure
from firebase_admin import credentials, firestore, initialize_app, storage
from geopy import distance
from math import sqrt, floor
import haversine

class GPXTracker():
    # def __init__(self, data_path, map_path, points):
    #     self.data_path = data_path
    #     self.points = points
    #     self.map_path = map_path
    # 
    #     self.result_image = Image
    #     self.x_ticks = []
    #     self.y_ticks = []

    def __init__(self, client):
        self.data = []
        self.db = client
        
    
    def tracker_route(self):
        gpx_file = open(f'G:\\tmp\\flask_test\\static\\activity_11926302489.gpx', 'r', encoding='utf-8')
        gpx = gpxpy.parse(gpx_file)
        
        data = gpx.tracks[0].segments[0].points
        
        start = data[0]
        finish = data[-1]

        df = pd.DataFrame(columns=['lon', 'lat', 'alt', 'time'])
        for point in data:
            df = pd.concat([df, pd.DataFrame([{'lon': point.longitude, 'lat' : point.latitude, 'alt' : point.elevation, 'time' : point.time}])], ignore_index=True)

        fig = Figure()
        ax = fig.subplots()
        #ax.plot([1, 2])
        ax.plot(df['lon'], df['lat'])
        # Save it to a temporary buffer.
        buf = BytesIO()
        fig.savefig(buf, format="png")
        # Embed the result in the html output.
        data = base64.b64encode(buf.getbuffer()).decode("ascii")
        
        return data
        
    def tracker_altitude(self):
        gpx_file = open(f'G:\\tmp\\flask_test\\static\\activity_11926302489.gpx', 'r', encoding='utf-8')
        gpx = gpxpy.parse(gpx_file)

        data = gpx.tracks[0].segments[0].points
        
        start = data[0]
        finish = data[-1]

        df = pd.DataFrame(columns=['lon', 'lat', 'alt', 'time'])
        for point in data:
            df = pd.concat([df, pd.DataFrame([{'lon': point.longitude, 'lat' : point.latitude, 'alt' : point.elevation, 'time' : point.time}])], ignore_index=True)

        fig = Figure()
        ax = fig.subplots()
        #ax.plot([1, 2])
        df['time'] = df['time'].dt.tz_localize(None)
        ax.plot(df['time'], df['alt'])
        # Save it to a temporary buffer.
        buf = BytesIO()
        fig.savefig(buf, format="png")
        # Embed the result in the html output.
        data = base64.b64encode(buf.getbuffer()).decode("ascii")
        
        return data
        
    def tracking(self, filepath=None):
    
        if filepath == None:
            return #filename = 'activity_11926302489.gpx'

        bucket = storage.bucket("nwitter-84742.appspot.com")
        blob = bucket.blob(filepath)
        # local_file_path = f"G:\\tmp\\flask_test\\temp\\{filename}"
        # blob.download_to_filename(local_file_path)
        download_file_stream = blob.download_as_string()
        
        #gpx_file = open(f'G:\\tmp\\flask_test\\static\\{filename}', 'r', encoding='utf-8')
        #gpx_file = open(local_file_path, 'r', encoding='utf-8')

        gpx = gpxpy.parse(download_file_stream)

        data = gpx.tracks[0].segments[0].points
        
        start = data[0]
        finish = data[-1]

        df = pd.DataFrame(columns=['lon', 'lat', 'alt', 'time'])
        for point in data:
            df = pd.concat([df, pd.DataFrame([{'lon': point.longitude, 'lat' : point.latitude, 'alt' : point.elevation, 'time' : point.time}])], ignore_index=True)

        points = []
        for track in gpx.tracks:
            for segment in track.segments: 
                for point in segment.points:
                    points.append(tuple([point.latitude, point.longitude]))

        json_data = {'gpx':f'{points}'}
        nweets_ref = self.db.collection('nweets')
        #nweets_ref.document('rVyyuJ2Noxf9PSlbKXwC').update(json_data)
        
        # all_nweets = [doc.to_dict() for doc in nweets_ref.stream()]
        # nweet = nweets_ref.document('rVyyuJ2Noxf9PSlbKXwC').get()
        # points2 = nweet.to_dict()['gpx']
        
        m = folium.Map( location=[df.lat.mean(), df.lon.mean() ], zoom_start=15, tiles=None)
        folium.TileLayer('openstreetmap', name='OpenStreet Map').add_to(m)
        #folium.PolyLine(eval(points2), color='red', weight=2.5, opacity=.5).add_to(m)
        folium.PolyLine(points, color='red', weight=2.5, opacity=.5).add_to(m)
        
        lat_start = df.iloc[0].lat
        long_start = df.iloc[0].lon
        
        lat_mid = df.iloc[200].lat
        long_mid = df.iloc[200].lon

        lat_end = df.iloc[-1].lat
        long_end = df.iloc[-1].lon

        # 시작점
        html_camino_start = """
            Start of day {camino_day}
            """ #.format(camino_day=camino_day)
        popup = folium.Popup(html_camino_start, max_width=400)
        
        folium.vector_layers.CircleMarker(location=[lat_start, long_start], radius=9, color='white', weight=1, fill_color='green', fill_opacity=1, popup=html_camino_start).add_to(m)
        folium.RegularPolygonMarker(location=[lat_start, long_start], fill_color='white', fill_opacity=1, color='white', number_of_sides=3, radius=3, rotation=0, popup=html_camino_start).add_to(m)
        
        # 종착점
        html_camino_end = """
            End of day {camino_day}
            """ #.format(camino_day=camino_day)
        popup = html_camino_end

        folium.vector_layers.CircleMarker(location=[lat_end, long_end], radius=9, color='white', weight=1, fill_color='red', fill_opacity=1, popup=html_camino_end).add_to(m)
        folium.RegularPolygonMarker(location=[lat_end, long_end], fill_color='white', fill_opacity=1, color='white', number_of_sides=4, radius=3, rotation=45, popup=html_camino_end).add_to(m)

        # set the iframe width and height
        m.get_root().width = "800px"
        m.get_root().height = "600px"
        iframe = m.get_root()._repr_html_()
        total_time = ' '

        alt_dif = [0]
        time_dif = [0]
        dist_vin = [0]
        dist_hav = [0]
        dist_vin_no_alt = [0]
        dist_hav_no_alt = [0]
        dist_dif_hav_2d = [0]
        dist_dif_vin_2d = [0]
        for index in range(len(data)):
            if index == 0:
                pass
            else:
                start = data[index-1]
                
                stop = data[index]
                
                distance_vin_2d = distance.geodesic((start.latitude, start.longitude), (stop.latitude, stop.longitude)).m
                dist_dif_vin_2d.append(distance_vin_2d)
                
                distance_hav_2d = haversine.haversine((start.latitude, start.longitude), (stop.latitude, stop.longitude))*1000
                dist_dif_hav_2d.append(distance_hav_2d)
                
                dist_vin_no_alt.append(dist_vin_no_alt[-1] + distance_vin_2d)
                
                dist_hav_no_alt.append(dist_hav_no_alt[-1] + distance_hav_2d)
                
                alt_d = start.elevation - stop.elevation
                
                alt_dif.append(alt_d)
                
                distance_vin_3d = sqrt(distance_vin_2d**2 + (alt_d)**2)
                
                distance_hav_3d = sqrt(distance_hav_2d**2 + (alt_d)**2)
                        
                time_delta = (stop.time - start.time).total_seconds()
                
                time_dif.append(time_delta)
                        
                dist_vin.append(dist_vin[-1] + distance_vin_3d)
                
                dist_hav.append(dist_hav[-1] + distance_hav_3d)

        if floor(sum(time_dif)/60) >= 60:
            total_time = round(sum(time_dif)/3600, 1),' hour ', int(sum(time_dif)%60),' sec '
        else:
            total_time = floor(sum(time_dif)/60),' min ', int(sum(time_dif)%60),' sec '
        
        print(sum(time_dif))
        print(dist_vin[-1])
        print(total_time)
        
        return iframe, total_time