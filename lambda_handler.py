"""
Hawker Lambda App

Application code for invoking Hawker via the
AWS Lambda framework

Author: Kai Hirsinger
Since:  11th January 2016
"""

###########
# Imports #
###########

import config
import sys
import time
import urllib

from data_sources import sumologic
from slopeone import slopeone

#############
# Constants #
#############

# - None Defined - #

#####################
# Exception Classes #
#####################

# - None Defined - #

#######################
# Interface Functions #
#######################

def initialize(event, context):
    '''
    Entry point for calls to the recommender from
    AWS Lambda.

    Input:  event, context
            defined in AWS Lambda documentation.

    Output: json object containing appropriate
            response
    '''
    return slopeone.initialize(
        config.DB_HOST,
        config.DB_PORT,
        config.DB_NAME
    )

def update(event, context):
    '''
    Entry point for calls to the recommender from
    AWS Lambda.

    Input:  event, context
            defined in AWS Lambda documentation.

    Output: json object containing appropriate
            response
    '''
    sumo_conn = sumologic.SumoLogic(
        config.SUMO_ACCESS_ID,
        config.SUMO_ACCESS_KEY
    )
    print('Querying Sumo')
    sumo_data = sumologic.query(
        sumo_conn,
        config.SUMO_QUERY,
        config.SUMO_QUERY_RANGE
    )
    print('Updating model')
    updates = slopeone.update_from_sumo(
        sumo_data,
        config.DB_HOST,
        config.DB_PORT,
        config.DB_NAME
    )
    print('Updating predictions')
    preds = slopeone.update_interest_scores(
        db_url=config.DB_HOST,
        db_port=config.DB_PORT,
        db_name=config.DB_NAME
    )
    return {
        'updates':updates,
        'predictions':preds
    }

def predict(event, context):
    '''
    Entry point for calls to the recommender from
    AWS Lambda.

    Input:  event, context
            defined in AWS Lambda documentation.

    Output: json object containing appropriate
            response
    '''
    start = time.time()
    eventtype = urllib.unquote_plus(event['type'])
    result = slopeone.score_from_user(
        event['user'],
        config.DB_HOST,
        config.DB_PORT,
        config.DB_NAME
    )
    return {
        'count':len(result),
        'time': time.time() - start,
        'listings':[
            {'id':listing_id, 'score':score}
            for listing_id, score in result.items()
        ]
    }

################################
# Internal Functions & Classes #
################################

# - None Defined - #

#################
# Main Function #
#################

def main():
    import json

    init_status = initialize({}, {})
    print(init_status)
    update_status = update({}, {})
    print(update_status)

if __name__ == '__main__':
    main()
