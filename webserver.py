from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import cgi

# import SQLAlchemy related functions
from database_setup import Base, Restaurant, MenuItem
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# create session and connect to DB
engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


class webserverHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            if self.path.endswith("/restaurants/new"):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                output = ""
                output += "<html><body>"
                output += "<h1>Make a New Restaurant</h1>"
                output += "<form method='POST' enctype='multipart/form-data' action='/restaurants/new'>"
                output += "<input name='newRestaurantName' type='text' placeholder='New Restaurant Name'>"
                output += "<input type='submit' value='Create'>"
                output += "</form></body></html>"
                self.wfile.write(output)
                return

            if self.path.endswith("/edit"):
                id = self.path.split("/")[2]
                restaurant = session.query(Restaurant).get(id)
                if restaurant:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    output = ""
                    output = "<html><body>"
                    output += "<h1>" + restaurant.name + "</h1>"
                    output += "<form method='POST' enctype='multipart/form-data' action='/restaurants/%s/edit'>" % id
                    output += "<input name='newRestaurantName' type='text' placeholder='%s'>" % restaurant.name
                    output += "<input type='submit' value='Rename'>"
                    output += "</form>"
                    output += "</body></html>"
                    self.wfile.write(output)

            if self.path.endswith("/delete"):
                id = self.path.split("/")[2]
                restaurant = session.query(Restaurant).get(id)
                if restaurant:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    output = ""
                    output += "<html><body>"
                    output += "<h3>Are you sure you want to delete %s?</h3>" % restaurant.name
                    output += "<form method='Post' enctype='multipart/form-data' action='/restaurants/%s/delete'>" % id
                    output += "<input type='submit' value='Delete'>"
                    output += "</form>"
                    output += "</body></html>"
                    self.wfile.write(output)
            if self.path.endswith("/restaurants"):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                output = ""
                output += "<html><body>"
                output += "<a href='/restaurants/new'><h1>Make a new restaurant</h1></a>"
                for restaurant in session.query(Restaurant):
                    output += restaurant.name
                    output += "<br>"
                    output += "<a href='/restaurants/%s/edit'>Edit </a>" % restaurant.id
                    output += "<a href='/restaurants/%s/delete'>Delete </a><br><br>" % restaurant.id
                output += "</body></html>"
                self.wfile.write(output)
                print output
                return

        except IOError:
            self.send_error(404, "File Not Found %s" % self.path)

    def do_POST(self):
        try:
            if self.path.endswith("/restaurants/new"):
                ctype, pdict = cgi.parse_header(
                    self.headers.getheader('content-type'))
                if ctype == 'multipart/form-data':
                    fields = cgi.parse_multipart(self.rfile, pdict)
                    messagecontent = fields.get('newRestaurantName')

                    # crete a new Restaurant
                    newRestaurant = Restaurant(name = messagecontent[0])
                    session.add(newRestaurant)
                    session.commit()

                    self.send_response(301)
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Location', '/restaurants')
                    self.end_headers()

            if self.path.endswith("/edit"):
                ctype, pdict = cgi.parse_header(
                    self.headers.getheader('content-type'))
                if ctype == 'multipart/form-data':
                    fields = cgi.parse_multipart(self.rfile, pdict)
                    messagecontent = fields.get('newRestaurantName')
                    id = self.path.split("/")[2]
                    restaurant = session.query(Restaurant).get(id)
                    if restaurant:
                        restaurant.name = messagecontent[0]
                        session.add(restaurant)
                        session.commit()
                        self.send_response(301)
                        self.send_header('Content-type', 'text/html')
                        self.send_header('Location', '/restaurants')
                        self.end_headers()

            if self.path.endswith("/delete"):
                id = self.path.split("/")[2]
                restaurant = session.query(Restaurant).get(id)
                if restaurant:
                    session.delete(restaurant)
                    session.commit()
                    self.send_response(301)
                    self.send_header('Content-type', 'text/html')
                    self.send_header('Location', '/restaurants')
                    self.end_headers()
        except:
            pass





# main() - instantiate our server and establish the port
def main():
    try:
        port = 8080
        # creates an instance of http server class
        server = HTTPServer(('',port), webserverHandler)
        print "Web server running on port %s" % port
        server.serve_forever()
    # ctrl - C
    except KeyboardInterrupt:
        print "^C entered, stopping web server..."
        server.socket.close()


if __name__ == '__main__':
    main()


# handler - what code to execute based on what is sent to the server