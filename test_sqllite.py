import sqlite3

connection = sqlite3.connect("stream_data.db")

if __name__ == '__main__':
    cursor = connection.cursor()
    query = "SELECT * FROM stream_params"
    cursor.execute(query)
    print(cursor.fetchall())