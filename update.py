import datetime
import lambda_handler
import sys

log_file = open('hawker_update_{}.log'.format(datetime.datetime.now().strftime('D%Y%m%d_T%H%M%S')), 'w')
sys.stdout = log_file
result = lambda_handler.update({}, None)
print('FINAL RESULT: {}'.format(result))
