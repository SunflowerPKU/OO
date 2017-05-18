"""
Import the MovieLens dataset into PostgreSQL
"""

import csv
import sqlalchemy
from secret import conn_str
'''
movies = []  # list of lists
movie_genres = []  # list of lists
genre_set = set()
'''
medicine = []
medicine_genres = []
genres = set()
sellers = set()
medicine_sellers = []

def to_int(s):
    try:
        return int(s)
    except:
        return None

def to_float(s):
    try:
        return float(s)
    except:
        return None


#medicineId, medicineName, medicineGenre, medicinePrice, SellerName, num
with open('ml-latest-small/medicine.csv', 'rb') as f:
    reader = csv.reader(f)
    reader.next()  # skip header
  
    for row in reader:
        medicineId, medicineName, medicineGenre, medicinePrice, sellerName, num, url, description = row
        medicine.append([to_int(medicineId),to_float(medicinePrice),to_int(num),medicineName, url, description])
        
        genres.add(medicineGenre)
        
        medicine_genres.append([to_int(medicineId),medicineGenre])
        
        sellers.add(sellerName)
        
        medicine_sellers.append([to_int(medicineId),sellerName])
   
engine = sqlalchemy.create_engine(conn_str)
conn = engine.connect()

conn.execute('INSERT INTO medicine VALUES (%s, %s, %s, %s, %s, %s)', *medicine)
conn.execute('INSERT INTO genres VALUES (%s)', *[(genre,) for genre in list(genres)])
conn.execute('INSERT INTO medicine_genres VALUES (%s, %s)', *medicine_genres)
conn.execute('INSERT INTO sellers VALUES (%s)', *[(seller,) for seller in list(sellers)])
conn.execute('INSERT INTO medicine_sellers VALUES (%s, %s)', *medicine_sellers)


conn.close()