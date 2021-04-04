# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import dateutil.parser
import babel
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from sqlalchemy import func

from forms import *

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(35))
    state = db.Column(db.String(5))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(10))
    genres = db.Column(db.ARRAY(db.String()))
    image_link = db.Column(db.String(120))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(65))
    seeking_talent = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(350))
    shows = db.relationship('Show', backref="Venue", lazy=True)

    def __repr__(self):
        return '<Venue {}{}>'.format(self.name, self.id)


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(35))
    state = db.Column(db.String(5))
    phone = db.Column(db.String(10))
    genres = db.Column(db.ARRAY(db.String()))
    image_link = db.Column(db.String(120))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(65))
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(350))
    shows = db.relationship('Show', backref="Artist", lazy=True)

    def __repr__(self):
        return '<Artist {}{}>'.format(self.name, self.id)


class Show(db.Model):
    __tablename__ = 'Show'

    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return '<Show {}{}>'.format(self.artist_id, self.venue_id)


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    all_areas = Venue.query.with_entities(func.count(Venue.id), Venue.city, Venue.state).group_by(Venue.city,
                                                                                                   Venue.state).all()
    data = []
    for area in all_areas:
        area_venues = Venue.query.filter_by(state=area.state).filter_by(city=area.city).all()
        venue_details = []
        for each_venue in area_venues:
            venue_details.append({
                "id": each_venue.id,
                "name": each_venue.name,
                "num_upcoming_shows": len(
                    db.session.query(Show).filter(Show.venue_id == 1).filter(Show.start_time >= datetime.now()).all())
            })
        data.append({
            "city": area.city,
            "state": area.state,
            "venues": venue_details
        })

    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_term = request.form.get('search_term', '')
    search_result = db.session.query(Venue).filter(Venue.name.ilike(f'%{search_term}%')).all()
    data = []

    for result in search_result:
        data.append({
            "id": result.id,
            "name": result.name,
            "num_upcoming_shows": len(db.session.query(Show).filter(Show.venue_id == result.id).filter(
                Show.start_time > datetime.now()).all()),
        })
    response = {
        "count": len(search_result),
        "data": data
    }
    return render_template('pages/search_venues.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    venue = Venue.query.get(venue_id)

    if not venue:
        return render_template('errors/404.html')

    upcoming_shows_query = db.session.query(Show).join(Artist).filter(Show.venue_id == venue_id).filter(
        Show.start_time > datetime.now()).all()
    upcoming_shows = []

    for show in upcoming_shows_query:
        upcoming_shows.append({
            "artist_id": show.artist_id,
            "artist_name": show.Artist.name,
            "artist_image_link": show.Artist.image_link,
            "start_time": show.start_time.strftime("%Y-%m-%d %H:%M:%S")
        })

    past_shows_query = db.session.query(Show).join(Artist).filter(Show.venue_id == venue_id).filter(
        Show.start_time < datetime.now()).all()
    past_shows = []

    for show in past_shows_query:
        past_shows.append({
            "artist_id": show.artist_id,
            "artist_name": show.Artist.name,
            "artist_image_link": show.Artist.image_link,
            "start_time": show.start_time.strftime('%Y-%m-%d %H:%M:%S')
        })

    data = {
        "id": venue.id,
        "name": venue.name,
        "genres": venue.genres,
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website": venue.website,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link,
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows),
    }

    return render_template('pages/show_venue.html', venue=data)


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    error = False
    name = request.form['name']
    city = request.form['city']
    state = request.form['state']
    address = request.form['address']
    phone = request.form['phone']
    genres = request.form.getlist('genres')
    image_link = request.form['image_link']
    facebook_link = request.form['facebook_link']
    website = request.form['website']
    seeking_talent = True if 'seeking_talent' in request.form else False
    if seeking_talent:
        seeking_description = request.form['seeking_description']
    else:
        seeking_description = ''

    try:
        venue = Venue(name=name, city=city, state=state, address=address, phone=phone, genres=genres,
                      facebook_link=facebook_link, image_link=image_link, website=website,
                      seeking_talent=seeking_talent, seeking_description=seeking_description)
        db.session.add(venue)
        db.session.commit()
    except:
        db.session.rollback()
        error = True
        flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
    finally:
        db.session.close()
        if error:
            flash('Venue ' + request.form['name'] + ' was successfully listed!')
    return render_template('pages/home.html')


@app.route('/venues/delete/<venue_id>')
def delete_venue(venue_id):
    # TODO: add a "Are you sure?" dialog box

    venue = Venue.query.get_or_404(venue_id)
    try:
        db.session.delete(venue)
        db.session.commit()
        return redirect('/')
    except:
        flash(f'An error occurred. Venue {venue_id} could not be deleted.')
    finally:
        db.session.close()
    return redirect('/venues')


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    data = db.session.query(Artist).all()

    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = request.form.get('search_term', '')
    search_result = db.session.query(Artist).filter(Artist.name.ilike(f'%{search_term}%')).all()
    data = []

    for result in search_result:
        data.append({
            "id": result.id,
            "name": result.name,
            "num_upcoming_shows": len(db.session.query(Show).filter(Show.artist_id == result.id).filter(
                Show.start_time > datetime.now()).all()),
        })

    response = {
        "count": len(search_result),
        "data": data
    }
    return render_template('pages/search_artists.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    artist_details = db.session.query(Artist).get(artist_id)

    if not artist_details:
        return render_template('errors/404.html')

    past_shows_query = db.session.query(Show).join(Venue).filter(Show.artist_id == artist_id).filter(
        Show.start_time > datetime.now()).all()
    past_shows = []

    for show in past_shows_query:
        past_shows.append({
            "venue_id": show.venue_id,
            "venue_name": show.Venue.name,
            "venue_image_link": show.Venue.image_link,
            "start_time": show.start_time.strftime('%Y-%m-%d %H:%M:%S')
        })

    upcoming_shows_query = db.session.query(Show).join(Venue).filter(Show.artist_id == artist_id).filter(
        Show.start_time > datetime.now()).all()
    upcoming_shows = []

    for show in upcoming_shows_query:
        upcoming_shows.append({
            "venue_id": show.venue_id,
            "venue_name": show.Venue.name,
            "venue_image_link": show.Venue.image_link,
            "start_time": show.start_time.strftime('%Y-%m-%d %H:%M:%S')
        })

    data = {
        "id": artist_details.id,
        "name": artist_details.name,
        "genres": artist_details.genres,
        "city": artist_details.city,
        "state": artist_details.state,
        "phone": artist_details.phone,
        "website": artist_details.website,
        "facebook_link": artist_details.facebook_link,
        "seeking_venue": artist_details.seeking_venue,
        "seeking_description": artist_details.seeking_description,
        "image_link": artist_details.image_link,
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows),
    }

    return render_template('pages/show_artist.html', artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.get(artist_id)

    if artist:
        form.name.data = artist.name
        form.city.data = artist.city
        form.state.data = artist.state
        form.phone.data = artist.phone
        form.genres.data = artist.genres
        form.facebook_link.data = artist.facebook_link
        form.image_link.data = artist.image_link
        form.website.data = artist.website
        form.seeking_venue.data = artist.seeking_venue
        form.seeking_description.data = artist.seeking_description

    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    error = False
    artist = Artist.query.get(artist_id)
    artist.name = request.form['name']
    artist.city = request.form['city']
    artist.state = request.form['state']
    artist.phone = request.form['phone']
    artist.genres = request.form.getlist('genres')
    artist.image_link = request.form['image_link']
    artist.facebook_link = request.form['facebook_link']
    artist.website = request.form['website']
    artist.seeking_venue = True if 'seeking_venue' in request.form else False
    if artist.seeking_venue:
        artist.seeking_description = request.form['seeking_description']
    else:
        artist.seeking_description = ''
    try:
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        flash('An error occurred. Artist could not be changed.')
    finally:
        db.session.close()
        if not error:
            flash('Artist was successfully updated!')

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = Venue.query.get(venue_id)

    if venue:
        form.name.data = venue.name
        form.city.data = venue.city
        form.state.data = venue.state
        form.phone.data = venue.phone
        form.address.data = venue.address
        form.genres.data = venue.genres
        form.facebook_link.data = venue.facebook_link
        form.image_link.data = venue.image_link
        form.website.data = venue.website
        form.seeking_talent.data = venue.seeking_talent
        form.seeking_description.data = venue.seeking_description

    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    error = False
    venue = Venue.query.get(venue_id)
    try:
        venue.name = request.form['name']
        venue.city = request.form['city']
        venue.state = request.form['state']
        venue.address = request.form['address']
        venue.phone = request.form['phone']
        venue.genres = request.form.getlist('genres')
        venue.image_link = request.form['image_link']
        venue.facebook_link = request.form['facebook_link']
        venue.website = request.form['website']
        venue.seeking_talent = True if 'seeking_talent' in request.form else False
        venue.seeking_description = request.form['seeking_description']
        db.session.commit()
    except:
        error = True
        db.session.rollback()
    finally:
        db.session.close()
    if error:
        flash(f'An error occurred. Venue could not be changed.')
    else:
        flash(f'Venue was successfully updated!')

    return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    error = False
    name = request.form['name']
    city = request.form['city']
    state = request.form['state']
    phone = request.form['phone']
    genres = request.form.getlist('genres'),
    facebook_link = request.form['facebook_link']
    image_link = request.form['image_link']
    website = request.form['website']
    seeking_venue = True if 'seeking_venue' in request.form else False
    if seeking_venue:
        seeking_description = request.form['seeking_description']
    else:
        seeking_description = ''

    try:
        artist = Artist(name=name, city=city, state=state, phone=phone, genres=genres, facebook_link=facebook_link,
                        image_link=image_link, website=website, seeking_venue=seeking_venue,
                        seeking_description=seeking_description)
        db.session.add(artist)
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
    finally:
        db.session.close()
        if error:
            flash('Artist ' + request.form['name'] + ' was successfully listed!')
    return render_template('pages/home.html')


@app.route('/artists/delete/<artist_id>')
def delete_artist(artist_id):
    # TODO: add a "Are you sure?" dialog box

    artist = Artist.query.get_or_404(artist_id)
    try:
        db.session.delete(artist)
        db.session.commit()
        return redirect('/')
    except:
        flash(f'An error occurred. Venue {artist_id} could not be deleted.')
    finally:
        db.session.close()
    return redirect('/artists')


#  Shows
#  ----------------------------------------------------------------
@app.route('/shows')
def shows():
    shows_query = db.session.query(Show).join(Artist).join(Venue).all()

    data = []
    for show in shows_query:
        data.append({
            "venue_id": show.venue_id,
            "venue_name": show.Venue.name,
            "artist_id": show.artist_id,
            "artist_name": show.Artist.name,
            "artist_image_link": show.Artist.image_link,
            "start_time": show.start_time.strftime('%Y-%m-%d %H:%M:%S')
        })
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    error = False
    artist_id = request.form['artist_id']
    venue_id = request.form['venue_id']
    start_time = request.form['start_time']
    print(request.form)
    try:
        show = Show(artist_id=artist_id, venue_id=venue_id, start_time=start_time)
        db.session.add(show)
        db.session.commit()
    except:
        error = True
        flash('An error occurred. Show couldn\'t be listed.')
        db.session.rollback()
    finally:
        db.session.close()
        if error:
            flash('Show was successfully listed')
    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
