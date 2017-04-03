import random, string, requests, json, httplib2
from functools import wraps
from flask import Flask, render_template, request
from flask import redirect, url_for, flash, jsonify
from flask import session as login_session
from flask import make_response
# import SQLAlchemy related functions
from database_setup import Base, Restaurant, MenuItem, User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# JSON formatted file
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('/var/www/menuapp/menuapp/client_secrets.json', 'r').read())['web']['client_id']

# create session and connect to DB
engine = create_engine('postgresql://postgres:psql123@localhost/catalog')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' in login_session:
            return f(*args, **kwargs)
        else:
            flash('You are not allowed to access there')
            return redirect('/login')
        # Renaming the function name
    # decorated_function.func_name = f.func_name
    return decorated_function


@app.route('/login')
def showLogin():
    """ generates random anti-forgery state token with each GET
        then renders the login page while passing in this token
    """
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    """ Google OAuth sign in """
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    code = request.data
    try:
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        # exchanges auth code for credentials object
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the Authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # check if token is valid
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    # if there was an error in the token
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 50)
        response.headers['Content-Type'] = 'application/json'
        return response

    gplus_id = credentials.id_token['sub']

    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID"), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's user ID doesn't match app's ID"), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    login_session['provider'] = 'google'
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # see if user exists, if not, then make one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += '" style = "width: 300px; height: 300px;border-radius: '
    output += '150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;">'
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    """ Facebook OAuth sign in """

    # Prevents cross site reference forgery attack
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data

    # Exchange client token for long lived server side toekn with GET
    app_id = json.loads(open(
        '/var/www/menuapp/menuapp/fb_client_secrets.json', 'r').read())['web']['app_id']
    app_secret = json.loads(open(
        '/var/www/menuapp/menuapp/fb_client_secrets.json', 'r').read())['web']['app_secret']

    url = ('https://graph.facebook.com/oauth/access_token?'
           '&grant_type=fb_exchange_token&client_id=%s&client_secret=%s'
           '&fb_exchange_token=%s' % (app_id, app_secret, access_token))

    h = httplib2.Http()
    # Gets new longterm token
    result = h.request(url, 'GET')[1]
    data = json.loads(result)
    # Creates URL with new token
    userinfo_url = 'https://graph.facebook.com/v2.4/me'
    token = data["access_token"]

    url = userinfo_url + '?access_token=%s&fields=name,email,picture{url}' \
        % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]
    login_session['picture'] = data["picture"]["data"]["url"]
    # checks if user exists
    user_id = getUserID(login_session['email'])

    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += '" style = "width: 300px; height: 300px;border-radius: '
    output += '150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;">'
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


@app.route('/gdisconnect')
def gdisconnect():
    """ Disconnects and revokes permissions for Google OAuth """
    access_token = login_session['credentials']
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % \
        login_session['credentials']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result.status == 200:
        del login_session['credentials']
        del login_session['gplus_id']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/fbdisconnect')
def fbdisconnect():
    """ Disconnects and revoked permissions for Facebook OAuth """
    facebook_id = login_session['facebook_id']
    url = 'https://graph.facebook.com/%s/permissions' % facebook_id
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    del login_session['facebook_id']
    return "You have being logged out"


@app.route('/disconnect')
def disconnect():
    """ Ends session, calls respective OAuth provider, if used """
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
        if login_session['provider'] == 'facebook':
            fbdisconnect()
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showRestaurants'))
    else:
        flash("You were not logged in to begin with")
        redirect(url_for('showRestaurants'))


@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/JSON/')
def restaurantMenuItemJSON(restaurant_id, menu_id):
    """ Returns specific restaurant menu by JSON call """
    item = session.query(MenuItem).filter_by(
        restaurant_id=restaurant_id, id=menu_id).one()
    return jsonify(MenuItems=item.serialize)


@app.route('/restaurant/<int:restaurant_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
    """ Returns specific restaurant menu by JSON call """
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(
        restaurant_id=restaurant_id).all()
    return jsonify(MenuItems=[i.serialize for i in items])


@app.route('/restaurant/JSON')
def restaurantJSON():
    """ Returns all restaurants by JSON call """
    restaurants = session.query(Restaurant)
    return jsonify(Restaurants=[r.serialize for r in restaurants])


@app.route('/')
@app.route('/restaurant')
def showRestaurants():
    """ Shows all restaurants to users, renders CRUD options
        if user is logged in
    """
    restaurants = session.query(Restaurant).all()
    if 'username' not in login_session:
        return render_template('publicrestaurants.html',
                               restaurants=restaurants)
    else:
        if restaurants:
            return render_template('restaurants.html',
                                   restaurants=restaurants)
        else:
            flash("No restaurants!")
            return render_template('restaurants.html',
                                   restaurants=restaurants)


@app.route('/restaurant/new', methods=['GET', 'POST'])
@login_required
def newRestaurant():
    """ Method to create a new restaurant """
    if request.method == 'POST':
        newRestaurant = Restaurant(name=request.form['name'],
                                   user_id=login_session['user_id'])
        session.add(newRestaurant)
        session.commit()
        flash("New restaurant created!")
        return redirect(url_for('showRestaurants'))
    else:
        return render_template('newrestaurant.html')


@app.route('/restaurant/<int:restaurant_id>/edit/', methods=['GET', 'POST'])
@login_required
def editRestaurant(restaurant_id):
    """ Allows users that created the restaurant to edit it """
    editedRestaurant = \
        session.query(Restaurant).filter_by(id=restaurant_id).one()
    # Make sure the user editing the restaurant is the one who created it
    if editedRestaurant.user_id != login_session['user_id']:
        flash('You are not authorized to edit this restaurant. ' +
              'Please create your own restaurant in order to edit.')
        return redirect(url_for('showRestaurants'))
    if request.method == 'POST':
        if request.form['name']:
            editedRestaurant.name = request.form['name']
        session.add(editedRestaurant)
        session.commit()
        flash("Restaurant edited!")
        return redirect(url_for('showRestaurants'))
    else:
        # USE THE RENDER_TEMPLATE FUNCTION BELOW TO SEE THE VARIABLES YOU
        # SHOULD USE IN YOUR EDITMENUITEM TEMPLATE
        return render_template('editrestaurant.html',
                               restaurant_id=restaurant_id,
                               restaurant=editedRestaurant)


@app.route('/restaurant/<int:restaurant_id>/delete/', methods=['GET', 'POST'])
@login_required
def deleteRestaurant(restaurant_id):
    """ Method to delete restaurants that you create """
    deleteRestaurant = \
        session.query(Restaurant).filter_by(id=restaurant_id).one()
    # Check the user deleting the restaurant is the one who created it
    if deleteRestaurant.user_id != login_session['user_id']:
        flash('You are not authorized to delete this restaurant. ' +
              'Please create your own restaurant in order to delete.')
        return redirect(url_for('showRestaurants'))
    if request.method == 'POST':
        session.delete(deleteRestaurant)
        session.commit()
        flash("Restaurant deleted!")
        return redirect(url_for('showRestaurants'))
    else:
        return render_template('deleterestaurant.html',
                               restaurant_id=restaurant_id,
                               restaurant=deleteRestaurant)


@app.route('/restaurant/<int:restaurant_id>/')
@app.route('/restaurant/<int:restaurant_id>/menu')
def restaurantMenu(restaurant_id):
    """ Shows menu of a specific restaurant """
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id)
    creator = getUserInfo(restaurant.user_id)

    if 'username' not in login_session or \
            creator.id != login_session['user_id']:
        return render_template('publicmenu.html',
                               restaurant=restaurant,
                               items=items,
                               creator=creator)
    if items.count() == 0:
        flash("Nothing in menu!")
        return render_template('menu.html', restaurant=restaurant, items=items)
    else:
        return render_template('menu.html', restaurant=restaurant, items=items)


@app.route('/restaurant/<int:restaurant_id>/new/', methods=['GET', 'POST'])
@login_required
def newMenuItem(restaurant_id):
    """ method to create new menu item """
    # Authorization to make sure user creating new menu-item created restaurant
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if restaurant.user_id != login_session['user_id']:
        flash('You are not authorized to create ' +
              'a menu-item for this restaurant.')
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    if request.method == 'POST':
        newItem = MenuItem(name=request.form['name'],
                           description=request.form['description'],
                           course=request.form['course'],
                           price=request.form['price'],
                           restaurant_id=restaurant_id,
                           user_id=login_session['user_id'])
        session.add(newItem)
        session.commit()
        flash("new menu item created!")
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        return render_template('newmenuitem.html', restaurant_id=restaurant_id)


@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/edit/',
           methods=['GET', 'POST'])
@login_required
def editMenuItem(restaurant_id, menu_id):
    """ Method to edit existing menu item """
    editedItem = session.query(MenuItem).filter_by(id=menu_id).one()
    # Authorization to make sure user editing menu-item created it
    if editedItem.user_id != login_session['user_id']:
        flash('You are not authorized to edit any ' +
              'menu-items for this restaurant.')
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    if request.method == 'POST':
        editedItem.name = request.form['name']
        editedItem.description = request.form['description']
        editedItem.course = request.form['course']
        editedItem.price = request.form['price']
        session.add(editedItem)
        session.commit()
        flash("Menu item edited!")
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        return render_template('editmenuitem.html',
                               restaurant_id=restaurant_id,
                               menu_id=menu_id,
                               item=editedItem)


@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/delete/',
           methods=['GET', 'POST'])
@login_required
def deleteMenuItem(restaurant_id, menu_id):
    """ Method to delete menu item """
    deleteItem = session.query(MenuItem).filter_by(id=menu_id).one()
    # Authorization to make sure user deleting menu-item created menu-item
    if deleteItem.user_id != login_session['user_id']:
        flash('You are not authorized to delete ' +
              'any menu-items for this restaurant.')
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    if request.method == 'POST':
        session.delete(deleteItem)
        session.commit()
        flash("Menu item deleted!")
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        return render_template('deletemenuitem.html',
                               restaurant_id=restaurant_id,
                               menu_id=menu_id,
                               item=deleteItem)


def getUserID(email):
    """ Returns the user id by email """
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


def getUserInfo(user_id):
    """ Returns user by id """
    user = session.query(User).filter_by(id=user_id).one()
    return user


def createUser(login_session):
    """ Creates a new user """
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
                   picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run()
