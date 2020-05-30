import operator
import os
import sqlite3

from flask import Flask, render_template, send_file

from config import config
from db import get_conn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)


@app.route('/')
def main():
    cursor = get_conn().cursor()
    cursor.execute('select demo_id, server, map, datetime from demos;')
    demos = cursor.fetchall()
    demos.sort(key=operator.itemgetter('datetime'), reverse=True)
    return render_template('index.html', demos=demos)


@app.route('/get/<demo_id>')
def download_demo(demo_id):
    cursor = get_conn().cursor()
    cursor.execute('select filepath from demos where demo_id=?', (demo_id,))
    filepath = cursor.fetchone()['filepath']
    filename = filepath.rsplit('/', 1)[1]
    return send_file(filepath, as_attachment=True, attachment_filename=filename)


if __name__ == '__main__':
    app.run()
