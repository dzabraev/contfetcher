#!/usr/bin/env python3
# coding=utf8

import re
import sqlite3
import os

def db_to_tsv():
  conn=sqlite3.connect('data/contfetcher.db')
  curs=conn.cursor()
  tables=[]
  regex=re.compile('urls_|buttons_|child_parent_')
  if not os.path.exists('data/dump'):
    os.makedirs('data/dump')
  #print curs.execute("SELECT name FROM sqlite_master").fetchall()
  for row in curs.execute("SELECT name FROM sqlite_master"):
    tabname=row[0]
    if regex.match(tabname) and 'index' not in tabname:
      tables.append(tabname)
  for tabname in tables:
    fname='data/dump/{}.tsv'.format(tabname)
    ftab=open(fname,'w')
    print(tabname,'--->',fname)
    res=curs.execute("SELECT * FROM {}".format(tabname))
    sd=''
    descr=res.description
    for desc in descr:
      colname=desc[0]
      sd+='{}\t'.format(colname)
    if len(sd)>0:
      sd=sd[:-1]+'\n'
    ftab.write(sd)
    for r in res:
      astr=''
      for attr in r:
        astr+='{}\t'.format(attr)
      if len(astr)>0:
        astr=astr[:-1]+'\n'

      ftab.write(astr)
    ftab.close()


if __name__=="__main__":
  db_to_tsv()