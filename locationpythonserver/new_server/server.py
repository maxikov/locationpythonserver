#!/usr/bin/env python

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn
import threading
import cgi
import re
import json
import os

import locationestimator
import locationresolver
import datamanager
import jsonparser

debug = True
json_parser = None
data_manafer = None
location_resolver = None
save_readings = False
respond_with_location = True

    

class HTTPRequestHandler(BaseHTTPRequestHandler):
 
    def address_string(self): #Fix for the slow response
        host, _ = self.client_address[:2]
        return host
 
    def do_POST(self):
        global debug, json_parser, data_manager, location_resolver, save_readings, respond_with_location
        if debug:
            print "Path:", self.path
        if None != re.search('/api/v1/process_wifi_gps_reading/*', self.path):
            ctype, _ = cgi.parse_header(self.headers.getheader('content-type'))
            if debug:
                print "ctype:", ctype
            if ctype == 'application/json':
                length = int(self.headers.getheader('content-length'))
                data = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
                if debug:
                    print "Length:", length, "data:", data
                json_str = data.keys()[0]
                timestamp, locname, wifi_data, gps_data = json_parser.parse_wifi_gps_json(json_str)
                locid = location_resolver.resolve_name(locname)
                if debug:
                    print timestamp, locid, wifi_data, gps_data
                if save_readings:
                    data_manager.save_one_reading(timestamp, locid, wifi_data, gps_data)
                    if not respond_with_location:
                        self.send_response(200, "Saved")
                if respond_with_location:
                    le = locationestimator.LocationEstimator(debug = debug)
                    probs = le.probabilities(wifi_data, gps_data, data_manager.wifi_stats, data_manager.gps_stats)
                    locid = le.estimate_location(probs)[0]
                    locname = location_resolver.resolve_id(locid)
                    response = json.dumps({locname: locid})
                    print "Will respond:", response
                    self.send_response(200, response)
                self.send_response(200, "OK, I didn't do anything")
        
    def do_GET(self):
        global debug
        if debug:
            print "GET received:", self.path
        if None != re.search("/admin/dashboard*", self.path):
            filespath = os.path.dirname(os.path.realpath(__file__))
            filename = os.path.join(filespath, "static", "dashboard.html")
            if debug:
                print filename
            f = open(filename, "r")
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            for line in f.readlines():
                self.wfile.write(line)
            self.wfile.close()
            f.close()
        else:
            self.send_response(404, "Not found")

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
 
    def shutdown(self):
        self.socket.close()
        HTTPServer.shutdown(self)
 
class SimpleHttpServer():
    def __init__(self, ip, port):
        global debug, json_parser, data_manager, location_resolver
        json_parser = jsonparser.JsonParser(debug = debug)
        data_manager = datamanager.DataManager(debug = debug)
        location_resolver = locationresolver.LocationResolver(debug = debug)
        self.server = ThreadedHTTPServer((ip,port), HTTPRequestHandler)
 
    def start(self):
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = False
        self.server_thread.start()
 
    def waitForThread(self):
        self.server_thread.join()
 
    def stop(self):
        self.server.shutdown()
        self.waitForThread()


def main():
    server = SimpleHttpServer('', 8080)
    print 'HTTP Server Running...........'
    server.start()
    server.waitForThread()
    
if __name__ == "__main__":
    main()