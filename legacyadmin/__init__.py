"""
Legacy Admin Project

This is the main package for the Legacy Admin project.
"""

try:
	import pymysql
except ImportError:
	pymysql = None
else:
	pymysql.install_as_MySQLdb()
