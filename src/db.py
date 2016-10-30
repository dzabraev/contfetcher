# coding=utf8

import sqlite3
import os
import sys

connect=None #connect object
cursor=None #cursor object

def dblog(msg):
  sys.stdout.write(msg)

def init():
  global connect
  global cursor
  if not os.path.exists('data'):
    os.makedirs('data')
  connect = sqlite3.connect('data/contfetcher.db')
  cursor = connect.cursor()

def close():
  pass

def commit():
  connect.commit()

def execute(request,params=None):
  dblog('{} {}\n'.format(request,params))
  if params!=None:
    return cursor.execute(request,params)
  else:
    return cursor.execute(request)

def table_exists(table_name):
  res=execute(
    "SELECT * FROM sqlite_master WHERE name=? and type='table';",
    (table_name,))
  return next(res,None)!=None



def create_url_table(table_name):
  if not table_exists(table_name):
    execute(
      '''CREATE TABLE {tn} (
      id                      INTEGER PRIMARY KEY AUTOINCREMENT,
      url                     TEXT UNIQUE,
      last_processing_date    INTEGER,
      insert_date             INTEGER,
      need_processing         INTEGER,
      processing              BOOL,
      error_type              INTEGER
      )
      '''.format(tn=table_name))
    cursor.execute("CREATE INDEX {tn}_url_index     ON {tn} (url)".format(tn=table_name))
    connect.commit()

def create_buttons_table(table_name):
  if not table_exists(table_name):
    execute(
      '''CREATE TABLE {tn} (
      id                      INTEGER PRIMARY KEY AUTOINCREMENT,
      text                    TEXT UNIQUE,
      tagname                 INTEGER,
      classname               INTEGER
      )
      '''.format(tn=table_name))
    #таблицы такого рода не очень большие (несколько сот элементов)
    #поэтому индекс не делаем
    connect.commit()


def create_child_parent_table(table_name):
  if not table_exists(table_name):
    execute(
      '''CREATE TABLE {tabname} (
        parent_id  INTEGER,
        child_id   INTEGER
      )
      '''.format(tabname=table_name))
    execute("CREATE INDEX {tn}_parent_index  ON {tn} (parent_id)".format(tn=table_name))
    execute("CREATE INDEX {tn}_child_index   ON {tn} (child_id)".format(tn=table_name))
    connect.commit()



