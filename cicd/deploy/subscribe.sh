# test
source .env


# test subscribe callback
curl "${VERIFY_URL}?hub.verify_token=${STRAVA_VERIFY_TOKEN}&hub.challenge=15f7d1a91c1f40f8a748fd134752feb3&hub.mode=subscribe"


# subscribe
curl -X POST https://www.strava.com/api/v3/push_subscriptions \
	  -F client_id=$STRAVA_CLIENT_ID \
	  -F client_secret=${STRAVA_CLIENT_SECRET} \
	  -F callback_url=${VERIFY_URL} \
	  -F verify_token=${STRAVA_VERIFY_TOKEN}

# view subscriptions
curl -G https://www.strava.com/api/v3/push_subscriptions \
	-d client_id=${STRAVA_CLIENT_ID} \
	-d client_secret=${STRAVA_CLIENT_SECRET}


# delete subscription
ID=
curl -X DELETE "https://www.strava.com/api/v3/push_subscriptions/${ID}?client_id=${STRAVA_CLIENT_ID}&client_secret=${STRAVA_CLIENT_SECRET}"