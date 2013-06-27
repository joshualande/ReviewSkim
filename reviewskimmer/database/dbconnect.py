from datetime import datetime
import pickle
import urllib
import pandas.io.sql as psql

class IMDBDatabaseConnector(object):
    """ Class to interface with the movie database. """

    def __init__(self, db):
        self.db=db
        self.cursor=self.db.cursor()

    def get_most_informative_features(self):
        return psql.frame_query("""SELECT * FROM rs_most_informative_features""", con=self.db)
    def set_most_informative_features(self, features):
        psql.write_frame(features, con=self.db, name='rs_most_informative_features', if_exists='replace', flavor='mysql')


    def delete_db(self):
        """ Delete all tables from the IMDB databse. """
        db=self.db
        db.query("DROP TABLE IF EXISTS rs_movies")
        db.query("DROP TABLE IF EXISTS rs_reviews")

    def create_bottom_100_all_time(self,bottom_100_all_time):
        """ bottom_100_all_time should be a pandas DataFrame that comes from
            the funtion reviewskimmer.imdb.charts.get_bottom_100_all_time. """
        psql.write_frame(bottom_100_all_time, con=self.db, name='rs_bottom_100_all_time', if_exists='replace', flavor='mysql')

    def get_bottom_100_all_time(self):
        return psql.frame_query("""SELECT * FROM rs_bottom_100_all_time""", con=self.db)

    def create_top_100_all_time(self,top_100_all_time):
        psql.write_frame(top_100_all_time, con=self.db, name='rs_top_100_all_time', if_exists='replace', flavor='mysql')

    def get_top_100_all_time(self):
        return psql.frame_query("""SELECT * FROM rs_top_100_all_time""", con=self.db)

    def create_top_grossing(self,top_grossing):
        psql.write_frame(top_grossing, con=self.db, name='rs_top_grossing', if_exists='replace', flavor='mysql')

    def get_top_grossing(self):
        return psql.frame_query("""SELECT * FROM rs_top_grossing""", con=self.db)

    def create_schema(self):
        """ Create the schema for the IMDB reviews databse.
        """
        db=self.db
        db.query("""
            CREATE TABLE rs_movies (
            rs_imdb_movie_id INT NOT NULL PRIMARY KEY,
            rs_movie_name TEXT NOT NULL,
            rs_budget TEXT,
            rs_gross TEXT,
            rs_imdb_movie_url TEXT NOT NULL,
            rs_imdb_poster_url TEXT,
            rs_imdb_poster_thumbnail_url TEXT,
            rs_db_insert_time DATETIME NOT NULL,
            rs_release_date DATE,
            rs_imdb_description TEXT
            );
        """);


        db.query("""
            CREATE TABLE rs_reviews (
            rs_imdb_movie_id INT NOT NULL,
            rs_imdb_reviewer_id INT NOT NULL,
            rs_reviwer TEXT,
            rs_review_movie_score INT,
            rs_review_date DATE NOT NULL,
            rs_num_likes INT,
            rs_num_dislikes INT,
            rs_review_spoilers BOOL NOT NULL,
            rs_imdb_review_ranking INT,
            rs_review_place TEXT,
            rs_imdb_review_url TEXT NOT NULL,
            rs_review_text TEXT
            );
        """)

    @staticmethod
    def format_time(time):
        if time is None:
            return None
        else:
            return time.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def format_url(url):
        if url is None:
            return None
        else:
            return urllib.unquote(url)


    def _add_movie_description(self,movie):
        """ Add in the IMDB descriptions of the movie. """
        c=self.cursor

        rs_imdb_movie_id=movie['imdb_movie_id']
        rs_movie_name=movie['movie_name']
        rs_db_insert_time=datetime.now()
        rs_budget=movie['budget']
        rs_gross=movie['gross']
        rs_release_date=self.format_time(movie['release_date'])
        rs_imdb_movie_url=self.format_url(movie['imdb_movie_url'])
        rs_imdb_poster_url=self.format_url(movie['imdb_poster_url'])
        rs_imdb_poster_thumbnail_url=self.format_url(movie['imdb_poster_thumbnail_url'])
        rs_imdb_description=movie['imdb_description']

        c.execute("""
            INSERT INTO rs_movies
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", 
            (rs_imdb_movie_id, rs_movie_name, rs_budget,
            rs_gross,  rs_imdb_movie_url, rs_imdb_poster_url, rs_imdb_poster_thumbnail_url,
            rs_db_insert_time, rs_release_date, rs_imdb_description,)
        )

        pass

    def add_movie(self,movie, force=False):
	""" Take in a movie dictionary skimmed from
	    reviewskimmer.imdb.scrape.scrape_movie and put the review
	    into the database. """
        imdb_movie_id=movie['imdb_movie_id']

        if self.in_movie_database(imdb_movie_id) or self.in_review_database(imdb_movie_id):
            if force:
                self.del_movie(imdb_movie_id)
            else:
                raise Exception("Cannot insert movie %s because it already exists in database." % imdb_movie_id)


        self._add_movie_description(movie)

        self._add_all_reviews(movie['reviews'])

    def _add_review(self,review):
	""" Add a review dictionary to the database.  This dict
        comes from reviewskimmer.imdb.scrape.scrape_movie to the
        database. """

        c=self.cursor

        rs_imdb_movie_id=review['imdb_movie_id']
        rs_imdb_reviewer_id=review['imdb_reviewer_id']
        reviwer=review['reviewer']
        review_movie_score=review['review_score']
        review_date=self.format_time(review['date'])
        review_num_likes=review['num_likes']
        review_num_dislikes=review['num_dislikes']
        review_spoilers=review['spoilers']
        imdb_review_ranking=review['imdb_review_ranking']
        review_place=review['review_place']
        imdb_review_url=self.format_url(review['imdb_review_url'])
        imdb_review_text=review['imdb_review_text']

        c.execute("""
            INSERT INTO rs_reviews 
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", 
            (rs_imdb_movie_id,rs_imdb_reviewer_id,reviwer,review_movie_score, 
                review_date,review_num_likes, review_num_dislikes, 
                review_spoilers, imdb_review_ranking,review_place, 
                imdb_review_url, imdb_review_text)
        )

        # This is necessary: http://mysql-python.sourceforge.net/MySQLdb.html
        self.db.commit()

    def _add_all_reviews(self,reviews):
        for review in reviews:
            self._add_review(review)

    def del_movie(self,imdb_movie_id):

        if not self.in_database(imdb_movie_id):
            raise Exception("Movie %s not in database" % imdb_movie_id)

        self._del_all_reviews_for_movie(imdb_movie_id)
        self._del_movie_description(imdb_movie_id)

    def _del_movie_description(self,imdb_movie_id):
        c=self.cursor

        c.execute("""
            DELETE FROM rs_movies
            WHERE rs_imdb_movie_id=%s""",
            (imdb_movie_id,)
        )
        self.db.commit()

    def _del_all_reviews_for_movie(self,imdb_movie_id):
	""" Remove every review for a movie specified by imdb_movie_id.
	"""
        c=self.cursor

        c.execute("""
            DELETE FROM rs_reviews
            WHERE rs_imdb_movie_id=%s""",
            (imdb_movie_id,)
        )
        self.db.commit()

    def get_nreviews(self,imdb_movie_id):
        return len(self.get_reviews(imdb_movie_id))

    def get_reviews(self,imdb_movie_id):
        """ Read all revies for the movie with a given imdb movie id.
        """
        c=self.cursor

        ex=c.execute("""
            select * FROM rs_reviews WHERE rs_imdb_movie_id=%s""",
            (imdb_movie_id,)
        )
        reviews=c.fetchall()
        return reviews

    def in_database(self,imdb_movie_id):
        return self.in_review_database(imdb_movie_id) and self.in_movie_database(imdb_movie_id)

    def in_review_database(self,imdb_movie_id):
        c=self.cursor

        ex=c.execute("""
            select * FROM rs_movies WHERE rs_imdb_movie_id=%s""",
            (imdb_movie_id,)
        )
        l=len(c.fetchall())
        assert l<=1
        return l==1

    def in_movie_database(self,imdb_movie_id):
        """ Test if a movie with a given imdb movie id is in the database. """
        c=self.cursor

        ex=c.execute("""
            select * FROM rs_movies WHERE rs_imdb_movie_id=%s""",
            (imdb_movie_id,)
        )
        l=len(c.fetchall())
        assert l<=1
        return l==1

    def get_newest_imdb_movie_id(self,movie_name):
        c=self.cursor
            
        ex=c.execute("""
            SELECT rs_imdb_movie_id 
            FROM rs_movies WHERE rs_movie_name=%s 
            ORDER BY rs_release_date DESC
            """,
            (movie_name,)
        )
        l=c.fetchall()
        if len(l)==0:
            return None
        else:
            return l[0][0]

    def get_imdb_movie_id(self,movie_name):
        """ Test if a movie with a given imdb movie id is in the database. """
        c=self.cursor

        ex=c.execute("""
            SELECT rs_imdb_movie_id FROM rs_movies WHERE rs_movie_name=%s""",
            (movie_name,)
        )
        l=c.fetchall()
        assert len(l)<=1
        if len(l)==1:
            print 'l=',l,'x'*100
            return l[0][0]
        else:
            return None
    
    def get_imdb_poster_thumbnail_url(self,imdb_movie_id):
        return self.get_movie(imdb_movie_id)['rs_imdb_poster_thumbnail_url']

    def get_movie_description(self,imdb_movie_id):
        if not self.in_review_database(imdb_movie_id):
            raise Exception("Movie %d is not in the database" % imdb_movie_id)
        return self.get_movie(imdb_movie_id)['rs_imdb_description']

    def get_reviews(self,imdb_movie_id):
        if not self.in_review_database(imdb_movie_id):
            raise Exception("Movie %d is not in the database" % imdb_movie_id)
    
        query="""SELECT * FROM rs_reviews WHERE rs_imdb_movie_id=%s""" % imdb_movie_id
        df_mysql = psql.frame_query(query, con=self.db)

        return df_mysql

    def get_movie(self,imdb_movie_id):
    
        query="""SELECT * FROM rs_movies WHERE rs_imdb_movie_id=%s""" % imdb_movie_id
        df_mysql = psql.frame_query(query, con=self.db)

        if len(df_mysql) == 0:
            raise Exception("Movie %d is not in the database" % imdb_movie_id)
        assert len(df_mysql) <= 1
        return df_mysql.ix[0]

    def get_movie_name(self,imdb_movie_id):
        return self.get_movie(imdb_movie_id)['rs_movie_name']

    def get_all_reviews(self):
        query="""SELECT * FROM rs_reviews"""
        df_mysql = psql.frame_query(query, con=self.db)
        return df_mysql

    def get_all_movies(self):
        query="""SELECT * FROM rs_movies"""
        df_mysql = psql.frame_query(query, con=self.db)
        return df_mysql

    def does_quotes_cache_exist(self):
        c=self.cursor
        c.execute("""
            SELECT count(*)
            FROM information_schema.TABLES
            WHERE (TABLE_SCHEMA = 'reviewskimmer') 
            AND (TABLE_NAME = 'rs_quotes_cache')""")
        l=c.fetchall()
        return l[0][0]==1


    def create_quotes_cache(self):
        """ Code to cache quotes """
        db=self.db
        db.query("""
            CREATE TABLE rs_quotes_cache (
            rs_imdb_movie_id INT NOT NULL PRIMARY KEY,
            rs_data LONGBLOB NOT NULL
            );
        """)

    def delete_quotes_cache(self):
        """ Delete all tables from the IMDB databse. """
        db=self.db
        db.query("DROP TABLE IF EXISTS rs_quotes_cache")

    def are_quotes_cached(self,imdb_movie_id):
        c=self.cursor

        ex=c.execute("""
            select * FROM rs_quotes_cache WHERE rs_imdb_movie_id=%s""",
            (imdb_movie_id,)
        )
        l=len(c.fetchall())
        return l>0

    def set_cached_quotes(self, imdb_movie_id, _data):
        c=self.cursor
        c.execute("""
            INSERT INTO rs_quotes_cache
            VALUES (%s,%s)""", 
            (imdb_movie_id, pickle.dumps(_data))
        )

        # This is necessary: http://mysql-python.sourceforge.net/MySQLdb.html
        self.db.commit()

    def get_cached_quotes(self, imdb_movie_id):
        if not self.are_quotes_cached(imdb_movie_id):
            raise Exception("No cached quotes for movie %s" % imdb_movie_id)
        c=self.cursor
        ex=c.execute("""
            select * FROM rs_quotes_cache WHERE rs_imdb_movie_id=%s""",
            (imdb_movie_id,)
        )
        l=c.fetchall()
        assert len(l)==1
        imdb_movie_id,_data=l[0]
        return pickle.loads(_data)

