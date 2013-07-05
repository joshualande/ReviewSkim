try:
    from collections import OrderedDict
except:
    from ordereddict import OrderedDict
import re
from pandas import DataFrame

from reviewskimmer.utils.strings import clean_unicode
from reviewskimmer.utils.web import get_soup

def _get_movie_list(url):

    soup = get_soup(url)
    votes=soup.find(text='Votes')
    current_movie=votes.next.next.next.next.next.next.next.next.next.next.next

    movies=[current_movie]
    for i in range(99):
        current_movie=current_movie.next.next.next.next.next.next.next.next.next.next.next.next.next.next.next.next
        movies.append(current_movie)

    ret=OrderedDict()

    imdb_movie_id=[]
    ranking=[]

    for i,movie in enumerate(movies):
        m=re.match('/title/tt(\d+)/',movie['href'])
        imdb_movie_id.append(int(m.groups()[0]))
        ranking.append(i)

    return DataFrame({'imdb_movie_id':imdb_movie_id,'ranking':ranking})

def get_top_100_all_time():
    df=_get_movie_list(url='http://www.imdb.com/chart/top')
    df.columns = ['rs_imdb_movie_id', 'rs_top_100_ranking']
    return df


def get_bottom_100_all_time():
    df=_get_movie_list(url='http://www.imdb.com/chart/bottom')
    df.columns = ['rs_imdb_movie_id', 'rs_bottom_100_ranking']
    return df

def get_top_box_office_by_year(year, number, debug=False):
    """ Pull out the 'number' highest-grosing
        movies of the year.
    """
    NUM_MOVIES_PER_PAGE=50

    sort='boxoffice_gross_us'

    def get_website(start,year):
        website='http://www.imdb.com/search/title?at=0&sort=%s&start=%s&title_type=feature&year=%s,%s' % (sort,start,year,year)
        return website

    n=1

    ret_list=OrderedDict()

    while n<number:
        print 'n=%s/%s' % (n,number)
        url_page = get_website(start=n,year=year)

        print url_page
        n+=NUM_MOVIES_PER_PAGE

        # I don't get why, but IMDB barfs when I specify a user agent???
        soup=get_soup(url_page,no_user_agent=True)

        # Match on <td class="number">, which refers to the ranking of the movie
        all_movies=soup.findAll('td',**{'class':"number"})

        for movie in all_movies:
            title_part=movie.next.next.next.next.next.next.next.next.next.next.next.next.next

            movie_name=clean_unicode(title_part.next)

            link=str(title_part['href'])
            m=re.match('/title/tt(\d+)/',link)
            groups=m.groups()
            assert len(groups)==1
            imdb_movie_id=int(groups[0])

            _year=title_part.next.next.next.next
            m=re.match(r'\((\d+)\)',_year)
            groups=m.groups()
            assert len(groups)==1
            year=int(groups[0])

            ret_list[imdb_movie_id]=movie_name

            # if only a few movies are requested
            if len(ret_list) == number:
                return ret_list

    return ret_list


def get_top_grossing_dataframe(years, number):

    rs_imdb_movie_id=[]
    rs_ranking=[]
    rs_year=[]

    for year in years:
        d=get_top_box_office_by_year(year, number, debug=False)
        for i,k in enumerate(d.keys()):
            rs_ranking.append(i)
            rs_imdb_movie_id.append(k)
            rs_year.append(year)

    return DataFrame({'rs_imdb_movie_id':rs_imdb_movie_id,'rs_ranking':rs_ranking,'rs_year':rs_year})

