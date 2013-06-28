#!/usr/bin/env python
from os.path import expandvars
import sys
import traceback
import os
import argparse

from flask import Flask
from flask import render_template
from flask import request

from reviewskimmer.analysis.summarize import ReviewSummarizer,CachedReviewSummarizer

from helpers import get_poster_thumbnail,format_quotes
from helpers import get_top_grossing_thumbnails,get_top_grossing_imdb_movie_ids
from helpers import try_load_poster,try_injest_movie
from helpers import get_top_for_website, get_bottom_for_website
from reviewskimmer.utils.list import flatten_dict

app = Flask(__name__)
app.config.from_envvar('REVIEWSKIMMER_CONFIG')


from reviewskimmer.database.dbconnect import IMDBDatabaseConnector
db = app.config['DB']
connector=IMDBDatabaseConnector(db)

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--amazon',default=False, action='store_true')
parser.add_argument('--debug',default=False, action='store_true')
parser.add_argument('--nocache',default=False, action='store_true')
args = parser.parse_args()

app.debug=True

def _get_top_grossing(connector,thumbnails=False):
    kwargs=dict(years=range(2013,2005,-1), movies_per_year=4)
    if thumbnails:
        top_grossing = get_top_grossing_thumbnails(connector,**kwargs)
    else:
        top_grossing = get_top_grossing_imdb_movie_ids(connector,**kwargs)
    return top_grossing

@app.route('/')
def index():
    top_grossing=_get_top_grossing(connector,thumbnails=True)
    return render_template('index.html', top_grossing=top_grossing)

def _get_summarizer(imdb_movie_id,nocache=False):
    ob=ReviewSummarizer if nocache else CachedReviewSummarizer
    summarizer=ob(connector=connector,
        imdb_movie_id=imdb_movie_id, num_occurances=5)
    return summarizer

@app.route('/search.html')
def search():
    movie_name = request.args.get('q', None)

    imdb_movie_id=connector.get_newest_imdb_movie_id(movie_name)

    if imdb_movie_id is not None:
        thumbnail_url_html=get_poster_thumbnail(imdb_movie_id,connector)

        summarizer = _get_summarizer(imdb_movie_id,nocache=args.nocache)

        top_quotes=summarizer.get_top_quotes()

        formatted_quotes = format_quotes(top_quotes)

        return render_template('search.html', 
                formatted_quotes=formatted_quotes,
                top_word_occurances=summarizer.get_top_word_occurances(),
                debug=args.debug,
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
    top=get_top_for_website(connector)
    bottom=get_bottom_for_website(connector)

    top=[get_poster_thumbnail(i,connector) for i in top]
    bottom=[get_poster_thumbnail(i,connector) for i in bottom]

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
        all_movies = flatten_dict(_get_top_grossing(connector,thumbnails=False)) + \
                get_top_for_website(connector) + \
                get_bottom_for_website(connector)
        for imdb_movie_id in all_movies:
            print 'Loading movie:',imdb_movie_id
            summarizer = _get_summarizer(imdb_movie_id,nocache=False)

        message='<div class="alert alert-success">The popular movies were cached!</div>'

    elif user_request == 'clearcache':
        connector.delete_quotes_cache()
        message='<div class="alert alert-success">The cache was cleared!<div>'
    elif user_request == 'injestmovie':
        try:
            imdb_movie_id=int(request.args.get('imdb_movie_id', None))
            message=try_injest_movie(imdb_movie_id,connector=connector)
        except Exception, ex:
            traceback.print_exc(sys.stdout)
            message='<div class="alert alert-error">Unable to injest movie! %s</div>' % ex
    elif user_request == 'getposter':
        try:
            imdb_movie_id=int(request.args.get('imdb_movie_id', None))
            message=try_load_poster(imdb_movie_id,connector=connector)
        except Exception, ex:
            message='<div class="alert alert-error">Unable to injest movie! %s</div>' % ex
    elif user_request is None:
        message=None
    else:
        raise Exception('Unrecognized request "%s"' % user_request)

    return render_template('secret.html',message=message)


if __name__ == '__main__':

    import argparse


    if args.amazon:
        app.run(host='0.0.0.0',port=80)
    else:
        app.run() 
