# Hawker Lambda Deployment Script
#
# Author: Kai Hirsinger
# Since:  12th January 2016
#
# Deploys Hawker to Lambda via the AWS
# CLI.

DEPLOY_FILE=hawker.zip
S3_BUCKET=hawker-deployment

echo "Creating package files"
mkdir ./temp
cp requirements.txt ./temp/
cp *_handler.py ./temp/
cp config.py ./temp/
cp ./slopeone ./temp/ -r
cp ./data_sources ./temp/ -r

echo "Building package"
cd ./temp
pip install -r requirements.txt -t ./
zip -r -q $DEPLOY_FILE *
mv $DEPLOY_FILE ../
cd ../

echo "Cleaning up"
rm ./temp -r

echo "Hawker deployment package created as $DEPLOY_FILE"

echo "Deploying 'initialize' package to Lambda"
aws lambda update-function-code \
--region us-west-2 \
--function-name Hawker-Init \
--zip-file fileb://$DEPLOY_FILE
--role arn:aws:iam::account-id:role/lambda_basic_execution  \
--handler lambda_handler.initialize \
#--runtime python2.7 \
#--timeout 15 \
#--memory-size 512

echo "Deploying 'update' package to Lambda"
aws lambda update-function-code \
--region us-west-2 \
--function-name Hawker-Update \
--zip-file fileb://$DEPLOY_FILE
--role arn:aws:iam::account-id:role/lambda_basic_execution  \
--handler lambda_handler.update \
#--runtime python2.7 \
#--timeout 15 \
#--memory-size 512

echo "Deploying 'prediciton' package to Lambda"
aws lambda update-function-code \
--region us-west-2 \
--function-name Hawker-Predict \
--zip-file fileb://$DEPLOY_FILE
--role arn:aws:iam::account-id:role/lambda_basic_execution  \
--handler lambda_handler.predict \
#--runtime python2.7 \
#--timeout 15 \
#--memory-size 512

echo "Cleaning up"
rm $DEPLOY_FILE

# Legacy S3 Upload code
#echo "Deploying package to S3"
#resource="/${S3_BUCKET}/${DEPLOY_FILE}"
#contentType="application/zip"
#dateValue=`date -R`
#stringToSign="PUT\n\n${contentType}\n${dateValue}\n${resource}"
#s3Key="AKIAIJT26N2VK6B24WFQ"
#s3Secret="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"
#signature=`echo -en ${stringToSign} | openssl sha1 -hmac ${s3Secret} -binary | base64`

#curl -X PUT -T "${DEPLOY_FILE}" \
#  -H "Host: ${S3_BUCKET}.s3.amazonaws.com" \
#  -H "Date: ${dateValue}" \
#  -H "Content-Type: ${contentType}" \
#  -H "Authorization: AWS ${s3Key}:${signature}" \
#  -k \
#  https://${S3_BUCKET}.s3-us-west-2.amazonaws.com/${DEPLOY_FILE}
