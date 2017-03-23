# Restaurant Menu Application
This project is a RESTful application built using the Flask python framework, Flask. 
It is implemented with Google and Facebook OAuth for easy login. 

Users are allowed to create, update and delete restaurants along with their respective menu items.

## Built With
* [Flask](http://flask.pocoo.org/) - Python Microframework
* [SQLAlchemy](http://www.sqlalchemy.org/) - Python SQL Toolkit
* [Jinja](http://jinja.pocoo.org/) - Python Template Engine
* [Bootstrap](http://getbootstrap.com/) - Front end Javascript, HTML, CSS Framework


## Prerequisites
Python 2.7.X

# Install Vagrant and VirtualBox
[Vagrant](https://www.vagrantup.com/) - Link to Vagrant
[VirtualBox](https://www.virtualbox.org/) - Link to VirtualBox

# Files
database_setup.py
project.py
client_secrets.json
fb_client_secrets.json

/static
/templates

## Running locally
1. Navigate to the local directory
2. Run the following commands to start the local development server
	'vagrant up'
	'vagrant ssh'
3. 'cd' to the project directory containing the files above
4. Run the following commands to initialize the database and project
	'python database_setup.py'
	'python project.py'
5. Navigate to the localhost port to view project

## License
This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments
Thank you to the Udacity FSWD nanodegree