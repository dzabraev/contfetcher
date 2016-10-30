# coding=utf8
import os
import socket
import sys
import marionette
import shutil
import datetime
import time
import signal
import select
import db
import re

import traverse_url
import comm
import cflib

cfgDir='config'
tmpDir="tmp"
profDir="profiles"
#DISPLAY=":99"
prime_number_for_files=10111 #prime number



# мини-туториал по sqlite https://docs.python.org/2/library/sqlite3.html


class unimpl(Exception): pass
class incorrect_rquest(Exception): pass
class internal_crash(Exception): pass

class ts: #traverse status
  processing=1
  ready=2
  error=3


class prerr:
  OK=0
  crash_trav=1
  crash_browser=2
  http_error=3
  network_error=4
  crash_main=5



def log(msg):
  sys.stdout.write(msg)



def get_cfg(cfg_fname):
  #cfg_fname must contain <config> variable!
  variables={}
  execfile(cfg_fname,variables)
  if 'config' not in variables:
    log(' cant extract config\n')
    sys.exit(1)
  config=variables['config']
  if config['profileName']=='default':
    config['profileName']='ykha450m.selenium'
  config['configFilename']=cfg_fname
  for host in config['hosts']:
    host['traverse_pids']=[]
  config['base_url']=get_base_url(config['start_url'])
  config['name']=config['base_url'].replace('.','_')
  return config


def check_uniq_names(configs):
  names=[]
  for cfg in configs:
    name=cfg['name']
    if name in names:
      log('ERROR: name "{}" non unique\n')
      sys.exit(1)
    names.append(name)

def prepare_and_copy_profile(host,cfg):
  marionette_port=host['marionette_port']
  srcProf='{}/{}'.format(profDir,cfg['profileName'])
  dstProf='{}/{}-{}'.format(tmpDir,cfg['profileName'],cfg['name'])
  if os.path.exists(dstProf):
    shutil.rmtree(dstProf)
  shutil.copytree(srcProf,dstProf)
  with open("{}/prefs.js".format(dstProf),"a") as prefsJs:
    prefsJs.write('''
        user_pref("marionette.contentListener", false);
        user_pref("marionette.defaultPrefs.port", {mar_port});
        user_pref("marionette.force-local", true);
      '''.format(mar_port=marionette_port))
  if host['hostname']!='127.0.0.1':
    #copy dstProf onto remote machine
    raise unimpl
  return dstProf


def redirectOutput(fname):
  logfd=os.open(fname,os.O_APPEND|os.O_CREAT|os.O_WRONLY,0777)
  os.write(logfd,'\n\n'+str(datetime.datetime.now())+'\n')
  os.dup2(logfd,1)
  os.dup2(logfd,2)



def display_already_running(host):
  DISPLAY=host['DISPLAY']
  if host['hostname']=='127.0.0.1':
    return not os.system('xdpyinfo -display {} > /dev/null 2>&1'.format(DISPLAY))
  else:
    raise unimpl


def make_cmd_for_print(cmd,args,environ):
  com=''
  for key in environ:
    cmd+='{}={} '.format(key,environ[key])
  com+=cmd+' '
  for arg in args:
    com+=arg+' '
  return com

def run_program(cmd,args,environ,host,**kwargs):
  logfile=kwargs.get('logfile')
  cmd2=make_cmd_for_print(cmd,args,environ)
  log('starting `{}`\n'.format(cmd2))
  if logfile:
    log('redirect output to {}\n'.format(logfile))
  args = [cmd] + args #for execve first arg must be the name of program
  if host['hostname']=='127.0.0.1':
    pid=os.fork()
    if pid==0:
      if logfile:
        logdir='/'.join(logfile.split('/')[:-1])
        if not os.path.exists(logdir):
          os.makedirs(logdir)
        redirectOutput( logfile )
      os.execve(cmd,args,environ)
  else:
    raise unimpl
  log('{} started, pid={}\n'.format(cmd.split('/')[-1],pid))
  return pid


def run_firefox(host,cfg,profilePath):
  cmd=host['firefox']
  args=['-marionette','--no-remote']
  environ={
          'DISPLAY':host['DISPLAY'],
          'XRE_PROFILE_PATH':profilePath,
  }
  logfile='{logdir}/browserlog/{name}/firefox-{pid}.log'.format(logdir=cfg['logdir'],pid=os.getpid(),name=cfg['name'])
  pid=run_program(cmd,args,environ,host,logfile=logfile)
  host['firefox_pid']=pid
  return pid


def run_virtual_display(host,cfg):
  if display_already_running(host):
    log('Xvfb :{} already exists\n'.format(host['DISPLAY']))
    return
  cmd=host['Xvfb']
  args=[host['DISPLAY'],'-screen','0','1024x768x16']
  environ={}
  logfile='{logdir}/Xvfb/{name}/Xvfb-{DISPLAY}.log'.format(DISPLAY=host['DISPLAY'],logdir=cfg['logdir'],name=cfg['name'])
  pid=run_program(cmd,args,environ,host,logfile=logfile)
  host['Xvfb_pid']=pid
  return pid

def run_x11vnc(host,cfg):
  cmd=host['x11vnc']
  args=['-display', host['DISPLAY'], '-reopen', '-forever']
  environ={}
  logfile='{logdir}/x11vnc/{name}/x11vnc-{DISPLAY}.log'.format(logdir=cfg['logdir'],name=cfg['name'],DISPLAY=host['DISPLAY'])
  pid=run_program(cmd,args,environ,host,logfile=logfile)
  host['x11vnc_pid']=pid
  return pid

def run_virtual_displays(configs):
  for cfg in configs:
    for host in cfg['hosts']:
      run_virtual_display(host,cfg)
      if cfg['run_x11vnc']:
        run_x11vnc(host,cfg)

def kill_program(host,pid,sig):
  if host['hostname']=='127.0.0.1':
    try:
      os.kill(pid,sig)
    except OSError:
      pass
  else:
    raise unimpl


def cleanup(configs):
  for cfg in configs:
    for host in cfg['hosts']:
      if 'firefox_pid' in host:
        log('pass SIGKILL to firefox, pid={}\n'.format(host['firefox_pid']))
        kill_program(host,host['firefox_pid'],signal.SIGKILL)

      if 'Xvfb_pid' in host:
        log('pass SIGKILL to Xvfb, pid={}\n'.format(host['Xvfb_pid']))
        kill_program(host,host['Xvfb_pid'],signal.SIGKILL)

      if 'x11vnc_pid' in host:
        log('pass SIGKILL to x11vnc, pid={}\n'.format(host['x11vnc_pid']))
        kill_program(host,host['x11vnc_pid'],signal.SIGKILL)

      for pid in host['traverse_pids']:
        sig=signal.SIGKILL
        log('pass sig {sig} to traverse, pid={pid}\n'.format(sig=sig,pid=pid))
        kill_program(host,pid,sig)

  db.close()


'''
  Протокол общения main process с traverse process
  1. main-->trav
    Отправка конфига
    {'action':'config','config':cfg}

  2. main-->trav
    Запрос на обработку url
    {'action':'url_processing','url':url}

  3. main<--trav
    Прием данных от trav
    {'action':'data','data':data}
    data={
      'type':'urls',
      'buttonId':buttonId,
      'urls':[url1,url2,...], #извлеченные url
    }
    data={
      'type':'files'
      'files':[file1,...]
    }
    file={
      'name':name,
      'data':data,
    }
  4. main<--trav
    {'action':'done'}
    Завершена обработка данного url
  5. main<--trav
    {'action':'error','msg':msg,'type':type}
    Произошла ошибка, msg -- текстовое представление ошибки
    type="crash_trav"|"crash_browser"|"http_error"|"network_error"
  6. main<--trav
    {'action':'cfId_request', 'features':features }
    features=[(tagName,text,className),...]
    Запрос cfId для кнопок с признаками features.
'''

def url_exists(table_name,url):
  res=db.execute('SELECT 1 FROM {} WHERE url=?'.format(table_name),(url,))
  row=next(res,None)
  return row and row[0]==1



def get_need_processing(url):
  act_cfgs=trav['cfg']['action_cfg']
  for acfg in act_cfgs:
    url_regex=acfg['selector']['url_regex']
    if url_regex.match(url):
      return True
  return False

def split_base_path(url):
  pa=url.split('/')
  base='/'.join(pa[0:3])
  path='/'+'/'.join(pa[3:])
  return (base,path)

def get_content_type(url):
  base,path=split_base_path(url)
  conn = httplib.HTTPConnection(base)
  conn.request("HEAD", path)
  res = conn.getresponse()
  content_type=res.getheader('Content-Type')
  return content_type



def create_symlinks(trav,url,url_id):
  #Создание символических ссылок на файлы, которые будут
  #созданы из url. Символические ссылки будут создаваться только
  #в том случае, если файлы, созданные из url уже существуют.
  tn=trav['urls_table_name']
  res=db.execute('SELECT last_processing_date FROM {tn} WHERE id={ID}'.format(tn=tn,ID=url_id))
  row=next(res,None)
  if row==None or row[0]==None:
    #Данной url не существует в БД
    raise internal_crash('url={} not found in table={}'.format(url,tn))
  last_processing_date=row[0]
  if last_processing_date==0:
    #еще не производилась обработка данной url.
    return
  act_cfgs=trav['cfg']['action_cfg']
  for acfg in act_cfgs:
    url_regex=acfg['selector']['url_regex']
    if url_regex.match(url):
      actions=acfg['actions'] #pairs (action_type,params)
      for act in actions:
        atype=act[0]
        if atype!='traverse':
          #это создание файла из контента url
          #значит второй параметр является суффиксом
          suffix=act[1]
          symlink_name=make_symlink_name(trav['url_processing'],url,suffix)
          realfile_name=make_depth(symlink_name)+make_filename(url,suffix)
          if os.path.exists(realfile_name):
            #Данная проверка нужна для того, что если url была обработана,
            #но файлы из нее создать не удалось. Например, readability
            #не сработал.
            os.symlink(realfile_name,symlink_name)

def url_processing_new_urls(trav,resp):
  new_urls_for_this_page=0
  urls_table_name=trav['urls_table_name']
  child_parent_table_name=trav['child_parent_table_name']
  child_parent_err_table_name=trav['child_parent_err_table_name']
  urls=resp['urls']
  parent_ID=trav['url_ID']
  last_processing_date=0
  insert_date=int(time.time())
  processing=False
  error_type=prerr.OK
  for url in urls:
    need_processing=get_need_processing(url)
    if not url_exists(urls_table_name,url):
      res=db.execute("INSERT INTO {tn} \
        (url,last_processing_date,insert_date,processing,need_processing,error_type) \
        VALUES (?,?,?,?,?,?,?,?)".format(tn=urls_table_name),
        (url,last_processing_date,insert_date,processing,need_processing,error_type)
      )
      child_id=res.lastrowid
    else:
      res=db.execute("SELECT id FROM {tn} where url=?".format(tn=urls_table_name),(url,))
      child_id=next(res)[0]
    res=db.execute("SELECT 1 FROM {cpt} where child_id={child_id} and parent_id={parent_id}".format(
              cpt=child_parent_table,
              child_id=child_id,
              parent_id=parent_id))
    if next(res,None)==None:
      #для parent_id данный url является новым, добавляем его в cpt.
      db.execute("INSERT INTO {cpt} (parent_id,child_id) VALUES ({parent_id},{child_id})".format(
        cpt=child_parent_table_name,
        parent_id=parent_id,
        child_id=child_id))
      #Строкой ниже происходит вставка в другую таблицу тех же значений.
      db.execute("INSERT INTO {cpt} (parent_id,child_id) VALUES ({parent_id},{child_id})".format(
        cpt=child_parent_err_table_name,
        parent_id=parent_id,
        child_id=child_id))

      new_urls_for_this_page+=1
    #Если из содержания данного url будут делаться файлы, 
    #и файлы из данной url уже созданы, то необходимо создать symlinks.
    #Если же файла нету, то symlinks будут созданы при создании файла.
    create_symlinks(trav,url,child_id)
      
  sqline_conn.commit()
  return new_urls_for_this_page

def make_dirs(filename):
  dname='/'.join(filename.split('/')[:-1])
  if not os.path.exists(dname):
    os.makedirs(dname)

def make_depth(filename):
  #example: data/foo/bar/test.html --> ../../../
  dep=''
  n=len(filename.split('/'))-1
  for _ in range(n):
    dep+='../'
  return dep

def get_base_url(url):
  #https://ria.ru/incidents/20161020/1479612182.html --> ria.ru
  return '.'.join( url.split('/')[2].split('.')[-2:] )

def get_base_name(url):
  #https://ria.ru/incidents/20161020/1479612182.html --> ria.ru_incidents_20161020_1479612182.html
  return '_'.join( url.split('/')[2:] )



def make_symlink_name(url_processing,url,suffix):
  #url является ссылкой на данные для создания файлов.
  #url_processing является ссылкой, для которой url является дочерней.
  #Тоесть при обходе url_processing была встречена url.
  base_url=get_base_url( url_processing )
  base_name=get_base_name( url )
  base_name_up=get_base_name( url_processing )
  hashval=int(hashlib.md5(base_name_up).hexdigest(),16) % prime_number_for_files
  filename='data/{base_url}/url_content/{hashval:05d}/{base_name_up}/{base_name}{suffix}'.format(
    name=name,
    hashval=hashval,
    fname=fname,
    base_name=base_name,
    suffix=suffix,
    base_name_up=base_name_up
  )
  return filename


def make_filename(url,suffix):
  # Соглашение по называнию файлов.
  # Контент каждого файла получается из контента url.
  # Содержимое url может быть извлечено как есть и сохранено в файл.
  # Содержимое url может быть преобразовано и сохранено в файл.
  # Если контент url сохраняется в файл как есть, то файл должен называться следующим образом
  # 1. из url необходимо отбросить protocol://
  # 2. заменить все "/" на "_"
  # Если контент url подвергается преобразованию, тогда название файла формируется
  # следующим образом. Необходимо выполнить пункты 1., 2. и к полученному назанию 
  # дописать суффикс.
  base_url=get_base_url( url )
  base_name=get_base_name( url )
  hashval=int(hashlib.md5(base_name).hexdigest(),16) % prime_number_for_files
  filename='data/{base_url}/files/{hashval}/{base_name}{suffix}'.format(name=name,hashval=hashval,fname=fname,base_name=base_name,suffix=suffix)
  return filename


def url_processing_new_files(trav,resp):
  files=resp['files']
  url_processing=trav['url_processing']
  url_processing_id=trav['url_id']
  for p in files:
    suffix=p['suffix']
    data=p['data']
    filename=make_filename(url,suffix)
    make_dirs(filename)
    #TODO не факт, что это бинарные данные, надо конвертировать данные из текста в бин.
    with open(filename,'wb') as f:
      f.write(data)
  res=db.execute('SELECT {utb}.id,{utb}.url FROM {cpt},{utb} WHERE \
      {cpt}.child_id={ID} and {cpt}.parent_id={utb}.id'.format(
        ID=url_processing_id,
        utb=trav['urls_table_name'],
        cpt=trav['child_parent_table_name']
      ))
  for parent_id,url in res:
    assert parent_id!=None and url!=None
    for p in files:
      suffix=p['suffix']
      #url является родительской для url_processing.
      #Тоесть при обходе url была извлечена url_processing
      symlink_name=make_symlink_name(url,url_processing,suffix)
      realfile_name=make_depth(symlink_name)+make_filename(url_processing,suffix)
      os.symlink(realfile_name,symlink_name)


def url_processing_new_data(trav,resp):
  if resp['type']=='urls':
    url_processing_new_urls(trav,resp)
  elif resp['type']=='files':
    url_processing_new_files(trav,resp)
  else:
    raise unimpl
  

def url_processing_done(trav):
  T=int(time.time())
  url=trav['url_processing']
  ID=trav['url_ID']
  urls_table_name=trav['urls_table_name']
  child_parent_err_table_name=trav['child_parent_err_table_name']
  log('processing url={} done\n'.format(url))
  db.execute(
      "UPDATE {tn} SET processing=0, last_processing_date={lpd}  WHERE id={ID}".format(
        tn=urls_table_name,lpd=T,ID=ID))
  db.execute("DELETE FROM {tn} WHERE parent_id={ID}".format(
    tn=child_parent_err_table_name,ID=ID))
  db.commit()
  trav['status']=ts.ready

def url_processing_error(trav,resp):
  type_str=resp['type']
  if type_str=="crash_trav":
    log('travserse process crash, host= {} , name= {}\n'.format(trav['hostname'],trav['name']))
    type_int=prerr.crash_trav
  elif type_str=="crash_browser":
    log('browser crash, host= {} , name= {}\n'.format(trav['hostname'],trav['name']))
    type_int=prerr.crash_browser
  elif type_str=="http_error":
    log('http error, host= {} , name= {}\n'.format(trav['hostname'],trav['name']))
    type_int=prerr.http_error
  elif type_str=="network_error":
    log('network error, host= {} , name= {}\n'.format(trav['hostname'],trav['name']))
    type_int=prerr.network_error
  trav['state']=ts.error
  trav['err_cause']=type_int
  urls_tn=trav['urls_table_name']
  db.execute("UPDATE {} SET error_type={} WHERE id={}".format(urls_tn,type_int,trav['url_ID']))
  db.commit()

def get_button_id(trav,feat):
  tagname,text,classname=feat
  btn=trav['buttons_table_name']
  res=db.execute(
    'SELECT id FROM {btn} where tagname=? and text=? and classname=?'.format(btn=btn),
    (tagname.decode('utf8'),text.decode('utf8'),classname.decode('utf8'))
  )
  row=next(res,None)
  if row:
    return row[0]
  else:
    return None


def url_processing_cfId_request(trav,resp):
  ids=[]
  btn=trav['buttons_table_name']
  features=resp['features']
  for feat in features:
    assert len(feat)==3
    ID=get_button_id(trav,feat)
    tagname=feat[0]
    text=feat[1]
    classname=feat[2]
    if not ID:
      res=db.execute(
        "INSERT INTO {} (tagname,text,classname) VALUES (?,?,?)".format(btn),
        (tagname.decode('utf8'),text.decode('utf8'),classname.decode('utf8'))
      )
      ID=res.lastrowid
      db.commit()
    ids.append(ID)
    for ID in ids:
      assert ID
  return ids

def get_trav_by_fd(travs,fd):
  for trav in travs:
    if trav['fd_r']==fd or trav['fd_w']==fd:
      return trav
  raise internal_crash('trav process with given fd={} not exists'.format(fd))

def receive_resp(travs):
  readfds=[trav['fd_r'] for trav in travs if trav['state']==ts.processing]
  if len(readfds)==0:
    return
  #TODO надо дожидаться не абы каких данных, а ждать пока literal не дойдет целиком
  #поскольку может быть ситуация, когда на первый дейскриптор пришел не весь литерал
  #и comm.liteal_recv() будет жать пока он не загрузится полностью, однако в это время
  #на второй дескриптор литерал придет целиком.
  fds=select.select(readfds,[],[])
  rfds=fds[0]
  for fd in rfds:
    trav=get_trav_by_fd(travs,fd)
    resp=comm.literal_recv(fd)
    url=trav['url_processing']
    if 'action' not in resp:
      log('ERROR: INCORRECT REQUEST')
      raise incorrect_rquest("absent 'action' field")
    act=resp['action']
    if act=='data':
      url_processing_new_data(trav,resp)
    elif act=='done':
      url_processing_done(trav)
    elif act=='error':
      url_processing_error(trav,resp)
    elif act=='cfId_request':
      ids=url_processing_cfId_request(trav,resp)
      assert len(ids)==len(resp['features'])
      comm.literal_send(trav['fd_w'],ids)
    else:
      raise incorrect_rquest(act)

def send_url_for_processing(trav,ID,url):
  request={'action':'url_processing','url':url}
  comm.literal_send(trav['fd_w'],request)
  trav['state']=ts.processing
  trav['url_processing']=url
  trav['url_ID']=ID

def all_travs_have_state(travs,states):
  for trav in travs:
    if trav['state'] not in states:
      return False
  return True

def get_url(trav):
  ID,url=(None,None)
  t=int(time.time())
  urls_table_name=trav['urls_table_name']
  res=db.execute(
    "SELECT id,url FROM {} where processing=0 and need_processing=1 LIMIT 1".format(
      urls_table_name))
  row=next(res,None)
  if row and row[0]:
    ID,url=row
    db.execute("UPDATE {} SET processing=1, need_processing=0 WHERE id={}".format(urls_table_name,ID))
    db.commit()
  log('processing url={}\n'.format(url))
  return (ID,url)


def send_rquests(travs):
  if all_travs_have_state(travs,(ts.error,)):
    return True
  for trav in travs:
    if trav['state']==ts.ready:
      ID,url=get_url(trav)
      if ID:
        send_url_for_processing(trav,ID,url)
  if all_travs_have_state(travs,(ts.ready,ts.error)):
    log('all done\n')
    return True
  return False

def exists_state(travs,states):
  for trav in travs:
    if trav['state'] in states:
      return True
  return False

def process_urls(travs):
  all_done=send_rquests(travs)
  while not all_done:
    receive_resp(travs)
    all_done=send_rquests(travs)
    if all_done and not exists_state(travs,(ts.processing,)):
      break



def open_traverse_proc(host,cfg):
  if host['hostname']=='127.0.0.1':
    r1,w1=os.pipe()
    r2,w2=os.pipe()
    pid=os.fork()
    if pid:
      os.close(w1)
      os.close(r2)
      r=r1
      w=w2
      host['traverse_pids'].append(pid)
      return (r,w,pid)
    else:
      os.close(r1)
      os.close(w2)
      r=r2
      w=w1
      traverse_url.traverse(r,w,host['marionette_port'])
      sys.exit(0)
  else:
    raise unimpl



def add_url_for_processing(tabname,url):
  res=db.execute("SELECT id,need_processing,processing FROM {tn} where url=?".format(tn=tabname),(url,))
  row=next(res,None)
  #Если данная url уже имеется в таблице и processing=False и need_processing=False, тогда
  #ей выставляется need_processing=True.
  if row!=None:
    #given url exists in table
    log('url={} exists in table={}\n'.format(url,tabname))
    ID,need_processing,processing=row
    if (not need_processing) and (not processing):
      db.execute("UPDATE {tn} SET need_processing=1 WHERE id={ID}".format(tn=tabname,ID=ID))
  else:
    #new url
    log('url={} not exists in table={}\n'.format(url,tabname))
    last_processing_date=0
    insert_date=int(time.time())
    processing=False
    need_processing=True
    error_type=prerr.OK
    res=db.execute("INSERT INTO {tn} \
      (url,last_processing_date,insert_date,processing,need_processing,error_type) \
      VALUES (?,?,?,?,?,?)".format(tn=tabname),
      (url,last_processing_date,insert_date,processing,need_processing,error_type)
    )
    ID=res.lastrowid
  db.commit()
  return ID

  
def main():
  '''
    1. читаются конфиги из config/
    2. ...
  '''
  configs=[]
  # 1. read configs
  for cfg_fname in os.listdir(cfgDir):
    if cfg_fname[-3:]!='.py':
      continue
    cfgPath='{}/{}'.format(cfgDir,cfg_fname)
    log('loading: {} ...'.format(cfgPath))
    cfg=get_cfg(cfgPath)
    log('ok\n')
    configs.append( cfg )
  check_uniq_names(configs)
  log('configs loaded\n')
  #2. run firefox for each config
  run_virtual_displays(configs) #create Xvfb displays on local and remote machines
  marionette_port=2828
  try:
    for cfg in configs:
      for host in cfg['hosts']:
        marionette_port+=1
        host['marionette_port']=marionette_port
        profilePath=prepare_and_copy_profile(host,cfg)
        run_firefox(host,cfg,profilePath)
  except OSError:
    cleanup(configs)
    raise

  db.init() #connect to database
  for cfg in configs:
    base_url=cfg['base_url']
    for hashval in range(prime_number_for_files):
      dname='data/{base_url}/url_content/{hashval:05d}'.format(hashval=hashval,base_url=base_url)
      if not os.path.exists(dname):
        os.makedirs(dname)



  # for each config create processes and attach them to corresponding browsers
  travs=[]
  for cfg in configs:
    urls_table_name='urls_{}'.format(cfg['name'])
    buttons_table_name='buttons_{}'.format(cfg['name'])
    child_parent_table_name='child_parent_{}'.format(cfg['name'])
    child_parent_err_table_name='child_parent_err_{}'.format(cfg['name'])
    cfg['urls_table_name']=urls_table_name
    cfg['buttons_table_name']=buttons_table_name
    cfg['child_parent_table_name']=child_parent_table_name
    cfg['child_parent_err_table_name']=child_parent_err_table_name
    db.create_url_table(urls_table_name)
    db.create_buttons_table(buttons_table_name)
    db.create_child_parent_table(child_parent_table_name)
    #Суть child_parent_err_table_name заключается в том, что при операции
    #traverse для некоторого url может произойти ошибка, например, разрыв
    #сетевого соединения, или бан на конечное время от веб-сервера.
    #В случае, если произошла ошибка считается, что traverse web-страницы
    #был не завершен. Поэтому traverse для данной url необходимо повторить.
    #При traverse необходимо отслеживать добавление новых url. При повторном
    #обходе необходимо игнорировать добавленные url с предыдущего(щих) неудачных traverse.
    #Если traverse завершился удачно, то из child_parent_err_table_name
    #требуется удалить все строки с parent_id==url_processing_id
    db.create_child_parent_table(child_parent_err_table_name)

    #Необходимо проверить таблицу urls_table_name. Если предыдущий вызов
    #программы завершился без ошибок, то в столбце processing должны быть
    #значения False(0). Если же в какой-либо строке при старте программы processing=True,
    #то это означает, что на предыдущем запуске было аварийное завершение данной программы.
    #В случае аварийного завершения на предыдущем запуске выполняется слудющий запрос.
    db.execute('UPDATE {tn} SET processing=0,need_processing=1,error_type={err} WHERE processing=1'.format(
      tn=urls_table_name,err=prerr.crash_main))
    db.commit()
    add_url_for_processing(urls_table_name,cfg['start_url'])

    for host in cfg['hosts']:
      for i in range(host['ntabs']):
        fd_r,fd_w,pid = open_traverse_proc(host,cfg)
        travs.append({
          'hostname':host['hostname'],
          'fd_r':fd_r,
          'fd_w':fd_w,
          'state':ts.ready,
          'pid':pid,
          'name':cfg['name'],
          'urls_table_name':urls_table_name,
          'buttons_table_name':buttons_table_name,
          'child_parent_table_name':child_parent_table_name,
          'child_parent_err_table_name':cfg['child_parent_err_table_name'],
          'cfg':cfg,
        })
        cflib.compile_regexes(cfg)
  
  
  try:
    process_urls(travs)
  except:
    cleanup(configs)
    raise

  cleanup(configs)

if __name__ == "__main__":
  res=main()
  sys.exit(res)
