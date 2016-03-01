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

#These should only be used for testing
DB_URL  = 'localhost'
DB_PORT = 27017
DB_NAME = 'slopeone'

#####################
# Exception Classes #
#####################

# - None Defined - #

#######################
# Interface Functions #
#######################

def initialize(db_url=DB_URL, db_port=DB_PORT, db_name=DB_NAME):
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

def update_from_sumo(sumo_views, db_url=DB_URL, db_port=DB_PORT, db_name=DB_NAME):
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

    #users = {}

    db = client[DB_NAME]

    #Update the listing_insterest collection
    print('Updating listing interest collection')
    collection = db['listing_interest']
    views_updated, views_inserted = 0, 0
    inserts = []

    for view in sumo_views:

        #Determine if listing/user combo already exists
        existing = collection.find_one({
            'listing_id':int(view['listingid']),
            'user_id':hash(view['username'])
        })

        #Update existing listing/user combo
        if existing:
            print('updating listing: {}, user: {}'.format(view['listingid'], view['username']))
            collection.update_one(
                {
                    'listing_id':int(view['listingid']),
                    'user_id':hash(view['username'])
                },
                {
                    '$inc':{'views':int(view['_count'])},
                    '$currentDate':{'lastModified':True}
                }
            )
            views_updated += 1

        #Create new listing/user combo
        else:
            inserts.append({
                'listing_id':int(view['listingid']),
                'user_id':hash(view['username']),
                'views':int(view['_count']),
                'interest':0.0,
                'updated':datetime.datetime.utcnow()
            })
            views_inserted += 1

    #Bulk insert using listing/user combos accumulated above
    print("inserting {} listing/user records into db".format(len(inserts)))
    collection.insert_many(inserts)

        #Keep track of users for updating users collection
        #try:
        #    users[hash(view['username'])] += int(view['_count'])
        #except KeyError:
        #    users[hash(view['username'])] = int(view['_count'])

    #Update the users collection
    #print('Updating users collection')
    #collection = db['users']
    #users_updated, users_inserted = 0, 0
    #for user_id,views in users.items():
    #    existing = collection.find_one({
    #        'user_id':user_id
    #    })
    #    if existing:
    #        print('updating user: {}'.format(user_id))
    #        collection.update_one(
    #            { 'user_id':user_id },
    #            {
    #                '$currentDate':{'lastModified':True},
    #                '$inc':{'listing_views':views}
    #            }
    #        )
    #        users_updated += 1
    #    else:
    #        print('inserting user: {}'.format(user_id))
    #        collection.insert_one({
    #            'user_id':user_id,
    #            'listing_views':views,
    #            'updated':datetime.datetime.utcnow()
    #        })
    #        users_inserted += 1

    return {
        'views_updated':views_updated,
        'views_inserted':views_inserted,
    #    'users_updated':users_updated,
    #    'users_inserted':users_inserted
    }

def update_interest_scores(threshold=0.5, db_url=DB_URL, db_port=DB_PORT, db_name=DB_NAME):
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
    db = client[DB_NAME]
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

def score_from_user(user_id, db_url=DB_URL, db_port=DB_PORT, db_name=DB_NAME):
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
