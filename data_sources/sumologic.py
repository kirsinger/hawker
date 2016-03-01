'''
Sumologic Interface Library

Author: Kai Hirsinger
Since:  September 2015

Provides a Python interface to the Sumologic API.
'''

###########
# Imports #
###########

import json
import logging
import requests

from copy import copy
from datetime import datetime, timedelta

#######################
# Interface Functions #
#######################

def query(conn, query, days_past):
    sumo_query = SumoQuery(days_past, conn)
    result = sumo_query.query(query)
    return result

##################################
# Internal Classes and Functions #
##################################

class SumoQuery(object):

    def __init__(self, days_past, conn):
        now = datetime.now()
        delta = timedelta(days_past)
        date_format = "%Y-%m-%dT%H:%M:%S"
        _from = (now - delta).strftime(date_format)
        _to   = now.strftime(date_format)
        self.range = _from, _to
        self.conn    = conn

    def set_connection(self, sumo_api_conn):
        self.conn = sumo_api_conn

    def set_days_past(self, days_ago):
        now = datetime.now()
        delta = timedelta(days_ago)
        date_format = "%Y-%m-%dT%H:%M:%S"
        _from = (now - delta).strftime(date_format)
        _to   = now.strftime(date_format)
        self.range = _from, _to

    def query(self, query):
        #Submit the search job
        search_job = self.conn.search_job(
            query,
            fromTime=self.range[0],
            toTime=self.range[1]
        )
        #Keep pinging the API until the job completes
        status = self.conn.search_job_status(search_job)
        while not(status['state'] == 'DONE GATHERING RESULTS'):
            status = self.conn.search_job_status(search_job)
            print(status['state'])
        #Reformat and return the results
        return [
            record['map']
            for record in self.conn.search_job_records(search_job)['records']
        ]

class SumoLogic:

    def __init__(self, accessId, accessKey, endpoint='https://api.au.sumologic.com'):
        self.endpoint = endpoint
        self.session = requests.Session()
        self.session.auth = (accessId, accessKey)
        self.session.headers = {'content-type': 'application/json', 'accept': 'application/json'}

    def delete(self, method, params=None):
        r = self.session.delete(self.endpoint + method, params=params)
        r.raise_for_status()
        return r

    def get(self, method, params=None):
        r = self.session.get(self.endpoint + method, params=params)
        r.raise_for_status()
        return r

    def post(self, method, params, headers=None):
        r = self.session.post(self.endpoint + method, data=json.dumps(params), headers=headers)
        r.raise_for_status()
        return r

    def put(self, method, params, headers=None):
        r = self.session.put(self.endpoint + method, data=json.dumps(params), headers=headers)
        r.raise_for_status()
        return r

    def search(self, query, fromTime=None, toTime=None, timeZone='UTC'):
        params = {'q': query, 'from': fromTime, 'to': toTime, 'tz': timeZone}
        r = self.get('/api/v1/logs/search', params)
        return json.loads(r.text)

    def search_job(self, query, fromTime=None, toTime=None, timeZone='UTC'):
        params = {'query': query, 'from': fromTime, 'to': toTime, 'timeZone': timeZone}
        r = self.post('/api/v1/search/jobs', params)
        return json.loads(r.text)

    def search_job_status(self, search_job):
        r = self.get('/api/v1/search/jobs/' + str(search_job['id']))
        return json.loads(r.text)

    def search_job_messages(self, search_job, limit=None, offset=0):
        params = {'limit': limit, 'offset': offset}
        r = self.get('/api/v1/search/jobs/' + str(search_job['id']) + '/messages', params)
        return json.loads(r.text)

    def search_job_records(self, search_job, limit=10000, offset=0):
        params = {'limit': limit, 'offset': offset}
        r = self.get('/api/v1/search/jobs/' + str(search_job['id']) + '/records', params)
        return json.loads(r.text)

    def collectors(self, limit=None, offset=None):
        params = {'limit': limit, 'offset': offset}
        r = self.get('/collectors', params)
        return json.loads(r.text)['collectors']

    def collector(self, collector_id):
        r = self.get('/collectors/' + str(collector_id))
        return json.loads(r.text), r.headers['etag']

    def update_collector(self, collector, etag):
        headers = {'If-Match': etag}
        return self.put('/collectors/' + str(collector['collector']['id']), collector, headers)

    def delete_collector(self, collector):
        return self.delete('/collectors/' + str(collector['collector']['id']))

    def sources(self, collector_id, limit=None, offset=None):
        params = {'limit': limit, 'offset': offset}
        r = self.get('/collectors/' + str(collector_id) + '/sources', params)
        return json.loads(r.text)['sources']

    def source(self, collector_id, source_id):
        r = self.get('/collectors/' + str(collector_id) + '/sources/' + str(source_id))
        return json.loads(r.text), r.headers['etag']

    def update_source(self, collector_id, source, etag):
        headers = {'If-Match': etag}
        return self.put('/collectors/' + str(collector_id) + '/sources/' + str(source['source']['id']), source, headers)

    def delete_source(self, collector_id, source):
        return self.delete('/collectors/' + str(collector_id) + '/sources/' + str(source['source']['id']))

    def create_content(self, path, data):
        r = self.post('/content/' + path, data)
        return r.text

    def get_content(self, path):
        r = self.get('/content/' + path)
        return json.loads(r.text)

    def delete_content(self):
        r = self.delete('/content/' + path)
        return json.loads(r.text)

    def dashboards(self, monitors=False):
        params = {'monitors': monitors}
        r = self.get('/dashboards', params)
        return json.loads(r.text)['dashboards']

    def dashboard(self, dashboard_id):
        r = self.get('/dashboards/' + str(dashboard_id))
        return json.loads(r.text)['dashboard']

    def dashboard_data(self, dashboard_id):
        r = self.get('/dashboards/' + str(dashboard_id) + '/data')
        return json.loads(r.text)['dashboardMonitorDatas']
