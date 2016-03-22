import os

#Application Database Details
DB_NAME = "slopeone"
DB_HOST = "54.69.234.90"
DB_PORT = 27017
#DB_HOST = "localhost"
#DB_PORT = 27017

#Customer Database Details
SJ_DB_NAME   = "SpotJobsProduct-TS"
SJ_DB_USER   = "sjpublic"
SJ_DB_PWD    = "123456"
SJ_DB_SERVER = "10.63.2.195"
SJ_DB_DRIVER = "SQL Server Native Client 11.0"

#Sumo API Details
SUMO_ACCESS_ID   = "suxr59TveIwE2B"
SUMO_ACCESS_KEY  = "CbBcTbcv1SA5yobiTmXkA4MKpXoe3mS6PZRKcdVf75S40u7nrVFYbuVpB00ZOqTd"
SUMO_QUERY       = """_source=enterprise_microsoft_logs__PROD__www_spotjobs_com | parse "*" as jsonobject | json field = jsonobject "EventId", "ExtendedProperties.UserAgent", "ExtendedProperties.ListingID", "ExtendedProperties.UserName" as eventid, useragent, listingid, username | formatDate(_messageTime, "MM/dd/yyyy HH:mm:ss:SSS") as timestamp | where !(useragent matches "*bot*") and !(useragent matches "*catalinbaroianu@yahoo.com*") and !(useragent matches "*crawler*") | where (eventid = 21) or (eventid = 22) | where !(username = "") | count by username, listingid, timestamp"""
SUMO_QUERY_RANGE = 1 # days

#AWS API Details
AWS_REGION = "us-west-2"
AWS_ACCESS_KEY_ID = "AKIAJYPPMH6NSNTR5MXQ"
AWS_SECRET_ACCESS_KEY = "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"

#Recomennder settings
REC_DIFF_CACHE = os.path.abspath("./predictors/cache/slope_diffs.pkl")
REC_FREQ_CACHE = os.path.abspath("./predictors/cache/slope_freqs.pkl")

def to_dict():
    return globals()
