"""
- Slope One -

Mongo implementation of the slope-one predictive algorithm
for use in collaborative filtering.

Author: Kai Hirsinger (kai@spotjobs.com)
Since:  2nd February 2016
"""

###########
# Imports #
###########

import datetime
import pymongo

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

def initialize(db_url, db_port, db_name):
    '''
    Re-initializes the model from scratch, wiping the
    current database.

    TODO: More informative failure message.

    Input:  None.
    Output: JSON compliant dict. Indicates status of initialization.
    '''
    client = pymongo.MongoClient(
        db_url,
        db_port
    )
    if db_name in client.database_names():
        try:
            print('dropping {}'.format(db_name))
            client.drop_database(db_name)
            return {'status':'initialized'}
        except Exception:
            return {'status':'initialization failure'}
    else:
        return {'status':'initialized'}

def update_from_sumo(sumo_views, db_url, db_port, db_name):
    '''
    Updates data used by the model using a SlopeOneData
    object.

    Input:  Sumo view data.
    Output: JSON compliant dict. Indicates status of update.
    '''
    print('Connecting to database')
    client = pymongo.MongoClient(
        db_url,
        db_port
    )

    db = client[db_name]

    #Update the listing_insterest collection
    print('Updating listing interest collection')
    collection = db['listing_interest']
    views_updated, views_inserted, views_skipped, views_removed = 0, 0, 0, 0
    inserts = {}

    for view in sumo_views:

        #Determine if listing/user combo already exists
        existing = collection.find_one({
            'listing_id':int(view['listingid']),
            'user_id':hash(view['username'])
        })

        #Update existing listing/user combo
        if existing:
            #Only update if view has not already been processed
            this_time = datetime.datetime.strptime(
                view['timestamp'],
                '%m/%d/%Y %H:%M:%S:%f'
            )
            last_updated = datetime.datetime.strptime(
                existing['updated'],
                '%m/%d/%Y %H:%M:%S:%f'
            )
            if not(this_time <= last_updated):
                collection.update_one(
                    {
                        'listing_id':int(view['listingid']),
                        'user_id':hash(view['username'])
                    },
                    {
                        '$inc':{'views':int(view['_count'])},
                        '$set':{'updated':view['timestamp']},
                        '$currentDate':{'lastModified':True}
                    }
                )
                views_updated += 1
            else:
                views_skipped += 1
                pass

        #Create new listing/user combo
        else:
            try:
                existing = ( view['listingid'], hash(view['username']) )
                this_time = datetime.datetime.strptime(
                    view['timestamp'],
                    '%m/%d/%Y %H:%M:%S:%f'
                )
                last_updated = datetime.datetime.strptime(
                    inserts[existing]['updated'],
                    '%m/%d/%Y %H:%M:%S:%f'
                )
                if this_time > last_updated:
                    inserts[existing]['views'] += int(view['_count'])
                    inserts[existing]['updated'] = view['timestamp']
                else:
                    inserts[existing]['views'] += int(view['_count'])
            except KeyError:
                inserts[(view['listingid'], hash(view['username']))] = {
                    'listing_id':int(view['listingid']),
                    'user_id':hash(view['username']),
                    'views':int(view['_count']),
                    'interest':0.0,
                    'updated':view['timestamp']
                }
            views_inserted += 1

    #Bulk insert using listing/user combos accumulated above
    if len(inserts) > 0:
        print("inserting {} listing/user records into db".format(len(inserts)))
        collection.insert_many(inserts.values())
    else:
        print("no listings to insert!")

    #Bulk remove any listing/user combos older than a month

    return {
        'views_updated':views_updated,
        'views_inserted':views_inserted,
        'views_removed':views_removed,
        'views_skipped':views_skipped
    }

def update_interest_scores(db_url, db_port, db_name, threshold=0.5):
    '''
    Calculates a set of interest scores for each user/listing
    combination in the database, and stores those above a
    certain threshold in the database.

    Input:  Double. Threshold, above which computed scores
            will be stored.
    Output: JSON compliant dict. Indicates status of update.
    '''
    client = pymongo.MongoClient(
        db_url,
        db_port
    )

    #Build up a userprefs object from the db
    userprefs = {}
    for record in client.slopeone.listing_interest.find():
        try:
            prefs = userprefs[record['user_id']]
            try:
                prefs[record['listing_id']] += record['views']
            except KeyError:
                prefs[record['listing_id']] = record['views']
            userprefs[record['user_id']] = prefs
        except KeyError:
            userprefs[record['user_id']] = {
                record['listing_id']:record['views']
            }

    #Train the model from userprefs
    model = SlopeOne()
    model.update(userprefs)

    #Store predictions for each user where rating is greater than threshold
    print("calculating predictions")
    predictions = {}
    for user,prefs in userprefs.items():
        predictions[user] = {
            listing:rating
            for listing,rating in model.predict(prefs).items()
            if rating > threshold
        }

    #Add predictions to database
    print("updating prediction database")
    db = client[db_name]
    collection = db['predictions']
    predictions_inserted, predictions_updated = 0, 0
    inserts = []
    for user,prefs in predictions.items():
        if prefs:
            for listing,score in prefs.items():
                existing = collection.find_one({
                    'user_id':user,
                    'listing_id':listing
                })
                if existing:
                    print("updating predictions for user: {}, listing: {}".format(user, listing))
                    try:
                        collection.update_one(
                            {
                                'user_id':user,
                                'listing_id':listing
                            },
                            {
                                '$currentDate':{'lastModified':True},
                                '$set':{'score':score}
                            }
                        )
                        predictions_updated += 1
                    except Exception:
                        return {
                            'error':'failure to insert record {}, {}'.format(user, listing)
                        }
                else:
                    inserts.append({
                        'user_id':user,
                        'listing_id':listing,
                        'score':score,
                        'updated':datetime.datetime.utcnow()
                    })
                    predictions_inserted += 1
    try:
        collection.insert_many(inserts)
        print("inserted {} new predictions".format(len(inserts)))
    except Exception:
        return {
            'error':'failure to insert predictions'
        }
    return {
        'predictions_inserted':predictions_inserted,
        'predictions_updated':predictions_updated
    }

def score_from_user(user_id, db_url, db_port, db_name):
    '''
    Input:  Int. ID of user.
    Output: JSON compliant dict. Indicates predictions for user.
    '''
    user   = hash(user_id)
    client = pymongo.MongoClient(
        db_url,
        db_port
    )
    return {
        view['listing_id']:view['score']
        for view in client.slopeone.predictions.find({'user_id':user})
    }

def score_from_prefs(user_prefs):
    '''
    Input:  List. Collection of ListingInterest objects.
    Output: JSON compliant dict. Indicates predictions for user.
    '''
    return None

###########
# Classes #
###########

class SlopeOne(object):
    '''
    Implements the Slope One algorithm for collaborative filtering
    based recommendations.
    '''

    def __init__(self):
        self.diffs = {}
        self.freqs = {}

    def update(self, data):
        for user, prefs in data.items():
            for item, rating in prefs.items():
                self.freqs.setdefault(item, {})
                self.diffs.setdefault(item, {})
                for item2, rating2 in prefs.items():
                    self.freqs[item].setdefault(item2, 0)
                    self.diffs[item].setdefault(item2, 0.0)
                    self.freqs[item][item2] += 1
                    self.diffs[item][item2] += rating - rating2
        for item, ratings in self.diffs.items():
            for item2, rating in ratings.items():
                ratings[item2] /= self.freqs[item][item2]

    def predict(self, userprefs):
        preds, freqs = {}, {}
        for item,rating in userprefs.items():
            for diffitem, diffratings in self.diffs.items():
                #predict only using items that co-occcur
                try:
                    freq = self.freqs[diffitem][item]
                except KeyError:
                    continue
                preds.setdefault(diffitem, 0.0)
                freqs.setdefault(diffitem, 0)
                preds[diffitem] += freq * (diffratings[item] + rating)
                freqs[diffitem] += freq
        return {
            item:(value / freqs[item])
            for item, value in preds.items()
            if item not in userprefs and freqs[item] > 0
        }

class SlopeOneData(object):

    def __init__(self):
        self.listing_interests = []
        self.users = []

    def load_views(self, view_data):
        return None

    def load_applications(self, view_data):
        return NotImplementedError(
            'This data source has not been implemented'
        )

    # Other data sources should be implemented as additional methods


################################
# Internal Functions & Classes #
################################

#################
# Main Function #
#################

def main():
    return None

if __name__ == '__main__':
    status = main()
    sys.exit(status)
