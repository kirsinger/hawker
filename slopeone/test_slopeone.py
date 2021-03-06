"""
- Slope One Unit Tests -

Contains tests for the slope_one module.

Author: Kai Hirsinger (kai@spotjobs.com)
Since:  2nd February 2016
"""

###########
# Imports #
###########

import json
import os
import pymongo
import slopeone
import unittest

from test_data import slope_one_toy_example

#############
# Constants #
#############

DB_URL  = 'localhost'
DB_PORT = 27017
DB_NAME = 'slopeone'

##############
# Unit Tests #
##############

class InterfaceTest(unittest.TestCase):

    def test_initialize(self):
        client = pymongo.MongoClient(
            DB_URL, DB_PORT
        )
        #Check initialization from scratch
        status = slopeone.initialize(DB_URL, DB_PORT, DB_NAME)
        self.assertEqual(status, {'status':'initialized'})
        self.assertFalse(DB_NAME in client.database_names())
        #Check initialization when db exists
        db = client[DB_NAME]
        collection = db['test_collection']
        collection.insert_one({'test':'this shouldnt be here'})
        status = slopeone.initialize(DB_URL, DB_PORT, DB_NAME)
        self.assertEqual(status, {'status':'initialized'})
        self.assertFalse(DB_NAME in client.database_names())

    def test_update_from_sumo(self):
        #Ensure we're starting with a clean database
        slopeone.initialize(DB_URL, DB_PORT, DB_NAME)

        #Insert the small data set
        with open('./test_data/sumo_data_1_days_updated.json') as data:
            sumo_data = json.load(data)
            status = slopeone.update_from_sumo(sumo_data, DB_URL, DB_PORT, DB_NAME)

        #Check the numbers
        self.assertEqual(
            status,
            {
                'views_updated': 0,
                'views_inserted': 538,
                'views_removed':0,
                'views_skipped':0
            }
        )

        #Insert the small data set again, ensure that nothing has changed
        status = slopeone.update_from_sumo(sumo_data, DB_URL, DB_PORT, DB_NAME)
        self.assertEqual(
            status,
            {
                'views_updated': 0,
                'views_inserted': 0,
                'views_removed':0,
                'views_skipped':538
            }
        )

        #Insert the larger test data set
        with open('./test_data/sumo_data_5_days.json') as data:
            sumo_data = json.load(data)
            status = slopeone.update_from_sumo(sumo_data, DB_URL, DB_PORT, DB_NAME)

        #Check the numbers
        self.assertEqual(
            status,
            {
                'views_updated': 28,
                'views_skipped': 431,
                'views_removed': 0,
                'views_inserted': 5455
            }
        )

    def test_update_interest_scores(self):
        #Ensure we're starting with a clean database
        slopeone.initialize(DB_URL, DB_PORT, DB_NAME)

        #Insert the test data set
        with open('./test_data/sumo_data_1_days_updated.json') as data:
            sumo_data = json.load(data)
            slopeone.update_from_sumo(sumo_data, DB_URL, DB_PORT, DB_NAME)

        #Update the interest scores
        status = slopeone.update_interest_scores(DB_URL, DB_PORT, DB_NAME)
        self.assertEqual(
            status,
            {
                'predictions_inserted':1207,
                'predictions_updated':0,
                'predictions_skipped':0
            }
        )

        #Update the interest scores again with the same data, ensure nothing is updated
        status = slopeone.update_interest_scores(DB_URL, DB_PORT, DB_NAME)
        self.assertEqual(
            status,
            {
                'predictions_inserted':0,
                'predictions_updated':0,
                'predictions_skipped':1207
            }
        )

        #Insert the larger test data set
        with open('./test_data/sumo_data_5_days.json') as data:
            sumo_data = json.load(data)
            slopeone.update_from_sumo(sumo_data, DB_URL, DB_PORT, DB_NAME)

        status = slopeone.update_interest_scores(DB_URL, DB_PORT, DB_NAME)
        self.assertEqual(
            status,
            {
                'predictions_inserted': 121927,
                'predictions_skipped': 514,
                'predictions_updated': 628
            }
        )


        #Clean up
        slopeone.initialize(DB_URL, DB_PORT, DB_NAME)

    def test_score_from_user(self):
        slopeone.initialize(DB_URL, DB_PORT, DB_NAME)
        with open('./test_data/sumo_data_1_days_updated.json') as data:
            sumo_data = json.load(data)
            slopeone.update_from_sumo(sumo_data, DB_URL, DB_PORT, DB_NAME)
        status = slopeone.update_interest_scores(DB_URL, DB_PORT, DB_NAME)
        client = pymongo.MongoClient(
            DB_URL, DB_PORT
        )
        user = client.slopeone.predictions.find()[10]['user_id']
        preds = slopeone.score_from_user(user, DB_URL, DB_PORT, DB_NAME)
        print(preds)

class SlopeOneTest(unittest.TestCase):

    def test_init(self):
        #Sanity checks
        predictor = slopeone.SlopeOne()
        self.assertIsInstance(predictor, slopeone.SlopeOne)
        self.assertIsInstance(predictor.diffs, dict)
        self.assertIsInstance(predictor.freqs, dict)
        self.assertEqual(predictor.diffs, {})
        self.assertEqual(predictor.freqs, {})

    def test_update(self):
        predictor = init_test_model()

        #An item should always be identical to itself
        expected = 0.0
        self.assertEqual(
            predictor.diffs["apple"]["apple"], expected,
            msg="Diff of item with itself was {}, expected {}".format(
                predictor.diffs["apple"]["apple"], expected
            )
        )

        #Summed diffs over all item pairs divided by frequency of co-occurences
        expected = -2.50
        item1, item2 = "apple", "bananna"
        self.assertEqual(
            predictor.diffs[item1][item2], expected,
            msg="Diff of items was {}, expected {}".format(
                predictor.diffs[item1][item2], expected
            )
        )

        #Items occurring only once should occur only once
        expected = 1.0
        self.assertEqual(
            predictor.freqs["mango"]["mango"], expected,
            msg="Item occurring only once occured {} times".format(
                predictor.freqs["mango"]["mango"]
            )
        )

    def test_predict(self):
        predictor = init_test_model()

        #Predict ratings for user with one item
        userprefs = {"bananna":2.5}
        prediction = predictor.predict(userprefs)
        self.assertEqual(prediction["apple"], 0.0)
        self.assertEqual(prediction["mango"], 0.5)

        #Predict ratings for user with multiple items
        #Predict ratings for user with no items
        userprefs = {}
        prediction = predictor.predict(userprefs)
        self.assertEqual(prediction, {})

class SlopeOneDataTest(unittest.TestCase):

    def test_init(self):
        data = slopeone.SlopeOneData()
        self.assertIsInstance(data, slopeone.SlopeOneData)
        self.assertIsInstance(data.listing_interests, list)
        self.assertIsInstance(data.users, list)
        self.assertEqual(data.listing_interests, [])
        self.assertEqual(data.users, [])

    def test_load_views(self):
        return None

################################
# Internal Functions & Classes #
################################

def init_test_model():
    model = slopeone.SlopeOne()
    model.update(slope_one_toy_example.example)
    return model

#################
# Main Function #
#################

if __name__ == "__main__":
    print("\nTesting Slope One Model:")
    unittest.main()
