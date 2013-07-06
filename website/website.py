#!/usr/bin/env python
from os.path import expandvars
import sys
import traceback
import os

import flask
from flask import Flask
from flask import render_template
from flask import request

from reviewskimmer.analysis.summarize import ReviewSummarizer,CachedReviewSummarizer

from reviewskimmer.website import helpers
from reviewskimmer.utils.list import flatten_dict

app = Flask(__name__)
application = app # This is needed by elastic beanstalk

from reviewskimmer.database.dbconnect import IMDBDatabaseConnector
import MySQLdb

@app.before_request
def before_request():
    flask.g.db=MySQLdb.Connection(host=os.environ['RDS_HOSTNAME'],
            user=os.environ['RDS_USERNAME'],
            port=int(os.environ['RDS_PORT']),
            passwd=os.environ['RDS_PASSWORD'],
            db=os.environ['RDS_DB_NAME'])
    flask.g.connector=IMDBDatabaseConnector(flask.g.db)

@app.teardown_request
def teardown_request(exception):
    flask.g.db = None
    flask.g.connector = None

app.debug=True

def _get_top_grossing(connector,thumbnails=False):
    kwargs=dict(years=range(2013,2005,-1), movies_per_year=4)
    if thumbnails:
        top_grossing = helpers.get_top_grossing_thumbnails(connector,**kwargs)
    else:
        top_grossing = helpers.get_top_grossing_imdb_movie_ids(connector,**kwargs)
    return top_grossing


def _get_summarizer(connector,imdb_movie_id):
    summarizer=CachedReviewSummarizer(connector=connector,
        imdb_movie_id=imdb_movie_id, num_occurances=5)
    return summarizer

@app.route('/')
def index():
    top_grossing=_get_top_grossing(flask.g.connector,thumbnails=True)
    return render_template('index.html', top_grossing=top_grossing)

@app.route('/search.html')
def search():
    movie_name = request.args.get('q', None)

    imdb_movie_id=flask.g.connector.get_newest_imdb_movie_id(movie_name)

    if imdb_movie_id is not None:
        thumbnail_url_html=helpers.get_poster_thumbnail(imdb_movie_id,flask.g.connector)

        summarizer = _get_summarizer(flask.g.connector,imdb_movie_id)

        top_quotes=summarizer.get_top_quotes()

        formatted_quotes = helpers.format_quotes(top_quotes)

        return render_template('search.html', 
                formatted_quotes=formatted_quotes,
                top_word_occurances=summarizer.get_top_word_occurances(),
                movie_name=movie_name,
                number_reviews=summarizer.get_nreviews(),
                imdb_movie_id=imdb_movie_id,
                thumbnail_url_html=thumbnail_url_html)

    else:
        return render_template('search.html', 
                movie_name=movie_name,
                imdb_movie_id=imdb_movie_id,
                )

@app.route('/charts.html')
def charts():
    top=helpers.get_top_for_website(flask.g.connector)
    bottom=helpers.get_bottom_for_website(flask.g.connector)

    top=[helpers.get_poster_thumbnail(i,flask.g.connector) for i in top]
    bottom=[helpers.get_poster_thumbnail(i,flask.g.connector) for i in bottom]

    return render_template('charts.html', top=top, bottom=bottom)


@app.route('/about.html')
def about():
    return render_template('about.html')

@app.route('/presentation.html')
def presentation():
    return render_template('presentation.html')

@app.route('/secret.html')
def secret():
    user_request = request.args.get('q', None)
    
    if user_request == 'cachepopular':
        all_movies = flatten_dict(_get_top_grossing(flask.g.connector,thumbnails=False)) + \
                helpers.get_top_for_website(flask.g.connector) + \
                helpers.get_bottom_for_website(flask.g.connector)
        for imdb_movie_id in all_movies:
            print 'Loading movie:',imdb_movie_id
            summarizer = _get_summarizer(imdb_movie_id)

        message='<div class="alert alert-success">The popular movies were cached!</div>'

    elif user_request == 'clearcache':
        flask.g.connector.delete_quotes_cache()
        message='<div class="alert alert-success">The cache was cleared!<div>'
    elif user_request == 'injestmovie':
        try:
            imdb_movie_id=int(request.args.get('imdb_movie_id', None))
            message=helpers.try_injest_movie(imdb_movie_id,connector=flask.g.connector)
        except Exception, ex:
            traceback.print_exc(sys.stdout)
            message='<div class="alert alert-error">Unable to injest movie! %s</div>' % ex
    elif user_request == 'getposter':
        try:
            imdb_movie_id=int(request.args.get('imdb_movie_id', None))
            message=helpers.try_load_poster(imdb_movie_id,connector=flask.g.connector)
        except Exception, ex:
            message='<div class="alert alert-error">Unable to injest movie! %s</div>' % ex
    elif user_request is None:
        message=None
    else:
        raise Exception('Unrecognized request "%s"' % user_request)

    return render_template('secret.html',message=message)


if __name__ == '__main__':
    app.run() 
