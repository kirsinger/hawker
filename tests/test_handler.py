"""
- AWS Lambda Handler Unit Tests -

Contains tests for the AWS Lambda handler
written for the Hawker recommendation engine.

Author: Kai Hirsinger (kai@spotjobs.com)
Since:  11th January 2016
"""

###########
# Imports #
###########

import lambda_handler
import unittest

##############
# Unit Tests #
##############

#TODO: Not sure if this can be unit tested
#class InterfaceUnitTest(unittest.TestCase):

    #def test_lambda_handler_initialization(self):


#####################
# Integration Tests #
#####################

class InterfaceIntegrationTest(unittest.TestCase):

    def test_lambda_handler_initialization(self):
        result = lambda_handler.initialize({}, None)
        print(result)

    def test_lambda_handler_update(self):
        result = lambda_handler.update({}, None)
        print(result)

    #def test_lambda_handler_recommendation(self):
    #    result = handler.lambda_handler({'type':'recommend', 'user':}, None)
    #    print(result)

#################
# Main Function #
#################

if __name__ == '__main__':
    unittest.main()
