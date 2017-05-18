"""
Import the MovieLens dataset into PredictionIO event server
This program generates a JSON file, while can be imported into PredictionIO by, e.g.,:
    pio import --appid 1 --input ml_ratings.json
"""

import csv
from datetime import datetime
import pytz
import predictionio

exporter = predictionio.FileExporter(file_name='ml_ratings.json')
counter = 0

with open('ml-latest-small/ratings.csv', 'rb') as f:
    reader = csv.reader(f)
    reader.next()  # skip header
    for row in reader:
        user_id, movie_id, rating, timestamp = row
        exporter.create_event(
            event="rate",
            entity_type="user",
            entity_id='movielens_' + user_id,  # add the prefix "movielens_" to all the username
            target_entity_type="item",
            target_entity_id=movie_id,
            properties={"rating": float(rating)},
            event_time=datetime.fromtimestamp(float(timestamp), pytz.utc)
        )
        counter += 1
        if counter % 1000 == 0:
            print('{} rows processed'.format(counter))

exporter.close()
