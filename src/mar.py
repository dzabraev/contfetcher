#!/usr/bin/python
# coding=utf8


import marionette
import time
import sys
import networkx as nx
import re
import os
import time
import traceback
import json
import datetime
import base64

PATH_IRRELEVANT=-1
PUSH_BUTTON_AWAY=-1
PUSH_BUTTON_OK=0
SUIT_BUTTON_NOT_EXISTS=-1
GRAPH_IRRELEVANT=-2

TRAVERSE_OK=0
TRAVERSE_EXCEPT=-2
TRAVERSE_NOTEND=-3
TRAVERSE_MSG={
  TRAVERSE_OK:'TRAVERSE_OK',
  TRAVERSE_EXCEPT:'TRAVERSE_EXCEPT',
  TRAVERSE_NOTEND:'TRAVERSE_NOTEND'
}
NOT_FOUND=-1
SUCCESS=0

JUMP_ROOT=-2

BUTTON_PUSH_OK="BUTTON_PUSH_OK"
BUTTON_LOST="BUTTON_LOST"


STORAGE_NOT_EXISTS=-3
LABEL_NOT_MATCH=-2
FINISHED=0
NOT_FINISHED=-1
ALL_BUTTONS_PUSHED=0


#ignByCfid_mk_ru=[1,2,3] + range(7,87)
ignByCfid_mk_ru=[1,2,3]+ range(9,82) + [83,84,85,86,87,88,89]





def get_bid(node,bad_bids,**kwargs):
  lpb=kwargs.get('lpb')
  predicate=kwargs.get('predicate', lambda cf_id: True)
  if lpb!=None:
    if lpb in node['ids'] and predicate(lpb):
      return lpb
  for bid in node['ids']:
    if (bid not in bad_bids) and predicate(bid):
      return bid
  return SUIT_BUTTON_NOT_EXISTS


def printArray(buttons):
  bts=''
  bts+='['
  l=len(buttons)
  for i in range(l):
    bts+=str(buttons[i])
    if i<l-1:
      bts+=','
      if i%10==0 and i!=0:
        bts+='\\n'
  bts+=']'
  return bts




def cleanSubgraph(G,rootIdx,nodeIdx):
  for idx in G.nodes():
    G.node[idx]['mark']=False
  G.remove_node(nodeIdx)
  queue=[rootIdx]
  while len(queue)>0:
    idx=queue.pop(0)
    G.node[idx]['mark']=True
    edges=G.edges(idx)
    for _,b in edges:
      if (b not in queue) and (not G.node[b]['mark']):
        queue.append(b)
  for idx in G.nodes():
    if G.node[idx]['mark']==False:
      G.remove_node(idx)



def arr_sub(A,B):
  #A/B
  return [a for a in A if a not in B]
  

def makeFname(href):
  return '_'.join(href.split('/')[2:]).replace('.','-')

class ButtonsGraph:
  def __init__(self,startPageUrl,**kwargs):
    self.n_pushbuttons_max=kwargs.get('n_pushbuttons_max',300)
    self.ignByCfid=kwargs.get('ignByCfid',[])
    self.ignByRegex=kwargs.get('ignByRegex',[])
    self.maxN=kwargs.get('maxN',2)
    cacheDir='.cache'
    self.tmpPath='/tmp'
    siteCatalog=self.makeShortName(startPageUrl)
    siteDir='{}/{}'.format(cacheDir,siteCatalog)
    hrefsDir='hrefs/{}'.format(siteCatalog)
    self.hrefs_fname='{}/hrefs.txt'.format(hrefsDir)
    if not os.path.exists(hrefsDir):
      os.makedirs(hrefsDir)
    logpath='log/{}'.format(siteCatalog)
    pageFileName=makeFname(startPageUrl)
    if not os.path.exists(logpath):
      os.makedirs(logpath)
    logfname='{}/{}'.format(logpath,pageFileName)
    self.logfile=open(logfname,'wb',0)
    dumpGraphName='{}'
    self.client = marionette.Marionette(host='localhost', port=2829)
    self.log('start session marionette\n')
    self.client.start_session()
    self.execute_script('document.cfFreezeDoc=false;')
    self.client.set_context("chrome")
    self.client.import_script('js/tab.js')
    self.tabIdx=self.execute_script('return openTab()')
    self.client.import_script( self.makeGlobalForCfJs() ) #make self.tabIdx as global variable for cf.js
    self.client.import_script('js/cf.js')
    client=self.client
    self.lastPushedButtonId=None
    self.G=nx.DiGraph()
    self.nodeCnt=0
    self.rootIdx=1
    self.currentNode=None
    #self.buttonsDescr={} #tuples (buttonId,text)
    self.buttons={}
    self.loadPage(url=startPageUrl)
    #self.pageUrl=self.getCurLoc()
    self.pageUrl=startPageUrl
    self.away_buttons=[]
    self.label=0
    self.hrefs=[]
    self.stats={}
    self.pushHist=[]
    self.maxButtonsPush=300
    self.uselessPredicate=lambda cf_id: self.stats[cf_id]['existContext']>0 or self.stats[cf_id]['nBlank']>0
    buttonsFname='{}/buttons.json'.format(siteDir)
    if os.path.exists(buttonsFname):
      self.log('read buttons from file "{}"\n'.format(buttonsFname) )
      with open(buttonsFname,'r') as f:
        buttons_json=f.read()
        BS=json.loads(buttons_json)
        buttons_json2=[]
        for b in BS:
          if 'img' in b:
            b2=b.copy()
            del b2['img']
            buttons_json2.append(b2)
          else:
            buttons_json2.append(b)
        escaped_buttons_json=json.dumps(buttons_json2).decode('utf8').replace('\n','\\n').replace('\\"',"\\\\\"")
        self.log('create cfPage object and import buttons\n')
        self.execute_script(u"window.cfGlobals[{tabIdx}].cfPage = new ContfetcherPage(JSON.parse('{}'));".format(
          escaped_buttons_json,tabIdx=self.tabIdx))
        for b in BS:
          if 'away' in b and b['away']:
            self.away_buttons.append(  b['cf_params']['cf_id']  )
          key=int(b['cf_params']['cf_id'])
          self.buttons[key]=b
          self.buttons[key]['updateImg']=True
    else:
      self.log('file with buttons "{}" not exists\n'.format(buttonsFname) )
      self.log('create cfPage object\n')
      res=self.execute_script("window.cfGlobals[{tabIdx}].cfPage = new ContfetcherPage();".format(tabIdx=self.tabIdx))
    self.addNode(0)
    self.initHrefs()
    self.updateButtonsDescr()
  def __del__(self):
    self.freezeDoc('false')
    if hasattr(self,'logfile'):
      self.logfile.close()
    if hasattr(self,'client'):
      self.client.delete_session()
    if hasattr(self,'buttonsLogFile'):
      self.buttonsLogFile.close()
  def makeGlobalForCfJs(self):
    fname='{tmpPath}/globalTmp{tabIdx}.js'.format(tmpPath=self.tmpPath,tabIdx=self.tabIdx)
    globs='''
      var tabIdx={tabIdx};
      var browser = window.cfGlobals[tabIdx].browser;
      var cfPage  = window.cfGlobals[tabIdx].cfPage;
      var curTab  = window.cfGlobals[tabIdx].curTab;
    '''.format(tabIdx=self.tabIdx)
    with open(fname,'w') as f:
      f.write(globs)
    return fname
  def log(self,msg,**kwargs):
    f=self.logfile
    needClose=False
    if 'file' in kwargs:
      f=kwargs['file']
    elif 'fname' in kwargs:
      f=open(fname,'a')
      needClose=True
    f.write(msg.encode('utf8'))
    f.flush()
    if needClose:
      f.close()
  def freezeDoc(self,b):
    self.execute_script('browser.contentDocument.cfFreezeDoc={};'.format(b))
  def updateButtonsDescr(self):
    #buttonsDescr=self.buttonsDescr
    client=self.client
    #bDescr=self.execute_script('return getButtonsDescr();')
    curBts=self.execute_script('return cfPage.getCurrentButtons();')
    for b in curBts:
      updateImg=False
      bid=b['cf_params']['cf_id']
      if bid not in self.buttons:
        self.buttons[bid] = b
        updateImg=True
      else:
        if 'updateImg' in self.buttons[bid]:
          updateImg=self.buttons[bid]['updateImg']
          del self.buttons[bid]['updateImg']
      text=b['features']['text']
      if updateImg and len(text)==0:
        elemXpath=self.execute_script('\
          doc=browser.contentDocument;return getXpathSimple(doc,getElementByCfId(doc,{}))'.format(bid))
        client.set_context('content')
        elem=client.find_element('xpath',elemXpath)
        assert elem!=None
        img=client.screenshot(elem)
        client.set_context('chrome')
        self.buttons[bid]['img']=img
  def loadPage(self,**kwargs):
    url=kwargs.get('url')
    ntry_ajax=kwargs.get('ntry_ajax',1000)
    try_ajax_timeout=kwargs.get('try_ajax_timeout',1.5)
    client=self.client
    self.execute_script('browser.contentWindow.location.changeLocation(true)')
    client.set_context("content")
    if url:
      self.log('LOADING {}\n'.format(url));
      client.navigate(url)
    else:
      self.log('RELOAD\n'.format(url));sys.stdout.flush()
      client.refresh()
    client.set_context("chrome")
    self.execute_script('browser.contentWindow.location.changeLocation(false)')
    ok=False
    if self.execute_script('return jquery_defined();'):
      self.log('jquery defined\n')
      self.execute_script('return replace_ajax();')
      self.execute_script('return replace_toggle();')
    else:
      self.log('jquery NOT defined\n')
  def loadPageOLD(self,**kwargs):
    url=kwargs.get('url')
    ntry_ajax=kwargs.get('ntry_ajax',1000)
    try_ajax_timeout=kwargs.get('try_ajax_timeout',1.5)
    client=self.client
    client.set_context("content")
    self.execute_script('document.cfFreezeDoc=false;')
    if url:
      self.log('LOADING {}\n'.format(url));
      self.execute_script('browser.contentWindow.location.changeLocation(true)')
      client.navigate(url)
      self.execute_script('browser.contentWindow.location.changeLocation(false)')
    else:
      self.log('refresh...'.format(url));sys.stdout.flush()
      self.execute_script('browser.contentWindow.location.changeLocation(true)')
      client.refresh()
      self.execute_script('browser.contentWindow.location.changeLocation(false)')
    ok=False
    client.set_context("chrome")
    if self.execute_script('return jquery_defined();'):
      self.log('jquery defined\n')
      self.execute_script('return replace_ajax();')
      self.execute_script('return replace_toggle();')
    else:
      self.log('jquery NOT defined\n')
    self.execute_script('browser.contentDocument.cfFreezeDoc=true;')
    #self.log(' ok\n')
  def evalHashPage(self):
    self.client.set_context(self.client.CONTEXT_CHROME)
    hashPage=self.execute_script('return hashPage(browser.contentDocument);')
    #hashPage=self.execute_script('return cfPage.hashPage_lastdata(gBrowser.contentDocument);')
    hashPage[2]=[int(h) for h in hashPage[2]]
    hashPage[2].sort()
    return hashPage
  def getNodeByHash(self,hval):
    G=self.G
    for idx in G.nodes():
      node=G.node[idx]
      if node['h']==hval:
        return idx
    return NOT_FOUND
  def addNode(self,buttonId,**kwargs):
    res=self._addNode(buttonId,**kwargs)
    self.log('CURRENT CONTEXT: nodeIdx={nodeIdx} hash={h} buttons={buttons}\n'.format(
      nodeIdx=self.currentNode,
      h=self.G.node[self.currentNode]['h'][0],
      buttons=self.G.node[self.currentNode]['h'][2]
    ))
    return res
  def suffix(self,idx,k):
    if k==0:
      return True
    s1=self.pushHist[idx+1-k:idx+1]
    s2=self.pushHist[-k:]
    if s1==s2:
      return True
    l1=len(s1)
    l2=len(s2)
    if l1==l2:
      return False
    l=min(l1,l2)
    s1=s1[-l:]
    s2=s2[-l:]
    if s1==s2:
      return True
    else:
      return False
  def get_n(self,idx):
    maxN=self.maxN
    d=0
    ph=self.pushHist
    for i in range(1, min(idx,maxN)+1 ):
      if ph[idx-i]==JUMP_ROOT or ph[-i-1]==JUMP_ROOT:
        return -1
      if ph[idx-i]!=ph[-i-1]:
        return i
    return -1
  def _addNode(self,buttonId,**kwargs):
    G=self.G
    stats=self.stats
    srcIdx=self.currentNode
    firstAdd=False
    if self.currentNode==None:
      firstAdd=True
    dstIdx=None
    if buttonId not in stats:
      stats[buttonId] = {'nPush':0,'existContext':0,'newHrefs':0,'nBlank':0}
    stat = stats[buttonId]
    stat['nPush']+=1
    hashPage=self.evalHashPage()
    ids=hashPage[2]
    ids=[int(b) for b in ids]
    for bId in ids:
      if bId not in stats:
        stats[bId]={'nPush':0,'existContext':0,'newHrefs':0, 'nBlank':0}
    idxs=self.G.nodes()
    for idx in idxs:
      if 'h' in  self.G.node[idx] and self.G.node[idx]['h']==hashPage:
        stat['existContext']+=1
        if not G.has_edge(self.currentNode,idx):
          self.G.add_edge(self.currentNode,idx,hist=[])
        self.currentNode=idx
        dstIdx=idx
        break
    if dstIdx==None:
      newNodeId=self.nodeCnt+1
      self.nodeCnt+=1
      self.G.add_node(newNodeId,h=hashPage,ids=[int(b) for b in hashPage[2]])
      if self.currentNode>0:
        self.G.add_edge(self.currentNode,newNodeId,hist=[])
      self.currentNode=newNodeId
      dstIdx=newNodeId
    if firstAdd:
      return
    allEdges=self.G.edges(srcIdx)
    bidHists=[]
    for a,b in allEdges:
      hists=self.G[a][b]['hist']
      for hist in hists:
        idx=hist['idx']
        if self.pushHist[idx]==buttonId:
          bidHists.append( (b,hist) )
    nh=0
    for bhist in bidHists:
      bIdx=bhist[1]['idx']
      bn=bhist[1]['n']
      b=bhist[0]
      k=min(nh,bn)
      if b==dstIdx and self.pushHist[bIdx-bn:bIdx]==self.pushHist[len(self.pushHist)-1-bn:-1]:
        self.log('ADD_NODE: {}-->{} exists history:  {}\n'.format(srcIdx,dstIdx,self.pushHist[bIdx-bn:bIdx]))
        return
      if self.suffix(bIdx,k):
        newn = self.get_n(bIdx)
        if newn>=0:
          newn = max(newn,bn)
          self.log('ADD_NODE: {}-->{} increase history {}:   {}\n'.format(srcIdx,dstIdx,newn,self.pushHist[bIdx-newn:bIdx]))
          bhist[1]['n']=newn
          nh=newn
        else:
          hi=self.G[srcIdx][b]['hist']
          self.log('ADD_NODE: {}-->{} remove (old) history:   {}\n'.format(srcIdx,dstIdx,self.pushHist[bIdx-bn:bIdx]))
          nh=bn
          hi.remove(bhist[1]) #remove history
          if len(hi)==0:
            self.log('ADD_NODE: {}-->{} remove edge({}-->{}):   {}\n'.format(srcIdx,dstIdx,srcIdx,b,self.pushHist[bIdx-nh:bIdx]))
            self.G.remove_edge(srcIdx,b)
            assert b!=dstIdx
          break
    self.log('ADD_NODE: {}-->{} add history:   {}\n'.format(srcIdx,dstIdx,self.pushHist[len(self.pushHist)-nh:]))
    G[srcIdx][dstIdx]['hist'].append({
      'idx':len(self.pushHist)-1,
      'n':nh
    })
  def gotoRoot(self):
    G=self.G
    self.pushHist.append(JUMP_ROOT)
    client=self.client
    self.execute_script('\
      let doc=browser.contentDocument;\
      let evt = doc.createEvent("MouseEvents");\
      evt.initEvent("click", true, true);\
      doc.body.dispatchEvent(evt);\
    ')
    newhash=self.evalHashPage()
    oldhash=self.G.node[self.rootIdx]['h']
    if newhash == oldhash:
      #success goto root
      self.log('GOTO ROOT: click body\n')
      self.currentNode=self.rootIdx
      return
    self.log('GOTO ROOT: reload page\n')
    self.loadPage(url=self.pageUrl)
    client.set_context('chrome')
    self.execute_script('cfPage.enumerateElements(0,0);')
    h1=G.node[self.rootIdx]['h']
    h2=self.evalHashPage()
    self.currentNode=self.rootIdx
    if h1!=h2:
      #TODO check that not exists node with h2
      self.updateNode(self.rootIdx,h2)
  def updateNode(self,nodeIdx,new_h):
    G=self.G
    node=G.node[nodeIdx]
    old_h=node['h']
    old_unpushed=node['ids']
    old_all=old_h[2]
    old_pushed=arr_sub(old_all,old_unpushed)
    new_all=new_h[2]
    new_unpushed=arr_sub(new_all,old_pushed)
    node['ids']=new_unpushed
    node['h']=new_h
    drop_ids=arr_sub(old_all,new_all)
    for a,b in G.edges(nodeIdx):
      pushed=G[a][b]['hist']
      pushed2=[hist for hist in pushed if self.pushHist[hist['idx']] not in drop_ids ]
      if len(pushed2)==0:
        G.remove_edge(a,b)
      else:
        G[a][b]['hist']=pushed2
    for b in new_all:
      if b not in self.stats:
        self.stats[b]={'nPush':0,'existContext':0,'newHrefs':0,'nBlank':0}
  def followPathVertexBid(self,path):
    #path= [ (srcIdx,dstIdx,BiD), ... ]
    for jump in path:
      a=jump[0]
      b=jump[1]
      bid=jump[2]
      res=self.pushButton(bid)
      if (res!=PUSH_BUTTON_OK) or (self.currentNode!=b):
        self.log('JUMP: failed  {a}-->{b}\n'.format(a=a,b=b))
        return PATH_IRRELEVANT
      else:
        self.log('JUMP: success {a}-->{b}\n'.format(a=a,b=b))
    return SUCCESS
  def historyOk(self,hist,pFuture):
    pHist=self.pushHist
    n=hist['n']
    idx=hist['idx']
    if n<len(pFuture):
      nFu=n
      nHi=0
    else:
      nFu=len(pFuture)
      nHi=n-nFu
    for i in range(1,nFu+1):
      if pHist[idx-i]!=pFuture[-i]:
        return False
    for i in range(1,nHi+1):
      if pHist[idx-i-nFu]!=pHist[-i]:
        return False
    return True
  def bfSearch(self,pred):
    G=self.G
    pHist=self.pushHist
    queue=[  (self.currentNode,[])  ]
    for a,b in G.edges():
      hists=G[a][b]['hist']
      for hist in hists:
        hist['mark']=False
    while len(queue)>0:
      idx,path=queue.pop(0)
      if pred(G.node[idx]):
        return (idx,path)
      allEdges=G.edges(idx)
      pFuture=[bId for (_,_,bId) in path]
      for a,b in allEdges:
        hists=G[a][b]['hist']
        for hist in hists:
          if not hist['mark'] and self.historyOk(hist,pFuture):
            bId=pHist[hist['idx']]
            queue.append(  (b,path+[(a,b,bId)])  )
            hist['mark']=True
    return (-1,[])
  def getButtonId(self,cf_id=None):
    # if cf_id != None, then goto node with
    # unpushed cf_id.
    G=self.G
    client=self.client
    rootIdx=1
    fo_ret=-1
    idx=self.currentNode
    cNode=G.node[idx]
    predicate=lambda cf_id: not self.uselessPredicate(cf_id) and cf_id not in self.ignByCfid
    if cf_id == None:
      self.log('GET BUTTON: try to find button in current context\n')
      bid=get_bid(cNode,self.away_buttons,lpb=self.lastPushedButtonId,predicate=predicate)
    else:
      self.log('GET BUTTON: find buttonId={} in current context\n'.format(cf_id))
      if cf_id in cNode['ids']:
        self.log('GET BUTTON: buttonId={} found\n'.format(bid))
        return cf_id
      else:
        self.log('GET BUTTON: buttonId={} not found\n'.format(cf_id))
        bid=-1
    if bid!=SUIT_BUTTON_NOT_EXISTS:
      self.log('GET BUTTON: buttonId={} found\n'.format(bid))
      #self.log('exist unpushed button({bid}) in current node({cnode})\n'.format(bid=bid,cnode=idx))
      return bid
    if cf_id==None:
      searchPred=lambda node: get_bid(node,self.away_buttons,predicate=predicate)!=SUIT_BUTTON_NOT_EXISTS
    else:
      searchPred=lambda node: cf_id in node['ids']
    while fo_ret==-1:
      self.log('GET BUTTON: do bfSearch\n')
      bf_ret,path=self.bfSearch(searchPred)
      if bf_ret==-1:
        if self.currentNode==self.rootIdx:
          #not one node with unpushed button
          self.log('GET BUTTON: not exists unpushed\n')
          return bf_ret
        else:
          self.log('GET BUTTON: not exists path from nodeIdx={} to node with unpushed button\n'.format(self.currentNode))
          self.gotoRoot()
          continue
      else:
        self.log('GET BUTTON: found path to unpushed {}\n'.format(path))
        fo_ret=self.followPathVertexBid(path)
        if fo_ret==0:
          #successfullt goto throw path
          if cf_id == None:
            res=get_bid( G.node[self.currentNode], self.away_buttons, lpb=self.lastPushedButtonId, predicate=predicate)
            self.log('GET BUTTON: buttonId={} found\n'.format(res))
            return res
          else:
            self.log('GET BUTTON: buttonId={} found\n'.format(cf_id))
            return cf_id
        else:
          #can't goto throw path; Seems tobe the path of graph
          #is nonactual. Try again.
          continue
    return -1 # Node with unpushed button not found
  def getCurLoc(self):
    client=self.client
    client.set_context("content")
    href=self.execute_script('return browser.contentWindow.location.origin;')
    client.set_context("chrome")
    return href
  def pushButtonOnly(self,cf_id,layer=None,**kwargs):
    #if cf_id not in self.stats:
    #  self.stats[cf_id] = {'nPush':0,'existContext':0,'newHrefs':0,'nBlank':0}
    #self.buttonsLogFile.write('{}\n'.format(cf_id))
    res=self._pushButtonOnly(cf_id,layer,**kwargs)
    stat=self.getHrefs()
    self.stats[cf_id]['newHrefs']=stat['newHrefs']
    if stat['newHrefs']==0:
      self.stats[cf_id]['nBlank']+=1
    else:
      self.stats[cf_id]['nBlank']=0
    return res
  def execute_script(self,script):
    self.log(u'EXECUTE SCRIPT: {}\n'.format(script))
    res=self.client.execute_script(script)
    self.log(u'EXECUTE SCRIPT RETURN: {}\n'.format(res))
    return res
  def makeAbsPath(self,path):
    return self.execute_script('return makeAbsPath("{}");'.format(path))
  def _pushButtonOnly(self,cf_id,layer=None,**kwargs):
    client=self.client
    href=self.pageUrl
    label=self.label
    G=self.G
    self.pushHist.append(cf_id)
    href1=self.execute_script('doc=browser.contentDocument; return doc.location.lastChangeLocation')
    if href1 != '':
      abs_href1=self.makeAbsPath(href1)
      if self.selfHref(abs_href1):
        self.hrefs.append(abs_href1)
    delay =kwargs.get('delay',1)
    sdelay=kwargs.get('sdelay',5)
    ntry=kwargs.get('ntry',1)
    self.label+=1
    self.lastPushedButtonId=cf_id
    #self.log('push cf_id={} node_id={}\n'.format(cf_id,self.currentNode))
    resPush=self.execute_script('return cfPage.pushButton({},{});'.format(cf_id,label))
    if resPush==BUTTON_LOST:
      self.log('PUSH BUTTON: buttonId={}  result=BUTTON_LOST\n'.format(cf_id))
      node=self.G.node[self.currentNode]
      if 'lostButtons' in node:
        node['lostButtons'].append(cf_id)
      else:
        node['lostButtons'] = [cf_id]
      return BUTTON_LOST
    else:
      while True:
        #self.log('.')
        res=self.execute_script('return cfPage.checkButtonPushed({});'.format(label))
        if res==FINISHED:
          break
        time.sleep(delay)
    self.log('PUSH BUTTON: buttonId={}  result=SUCCESS\n'.format(cf_id))
    if layer:
      self.execute_script('cfPage.enumerateElements({},{});'.format(cf_id,layer))
    else:
      self.execute_script('cfPage.enumerateElements({});'.format(cf_id))
    return PUSH_BUTTON_OK
  def pushButton(self,cf_id):
    self.log('PUSH BUTTON: buttonId={}\n'.format(cf_id))
    client=self.client
    G=self.G
    buttons=self.G.node[self.currentNode]['ids']
    self.G.node[self.currentNode]['ids']=[b for b in buttons if b!=cf_id]
    res=self.pushButtonOnly(cf_id)
    self.updateButtonsDescr()
    #if res==PUSH_BUTTON_AWAY:
    #  self.gotoRoot()
    #else:
    #  self.addNode(cf_id)
    self.addNode(cf_id)
    return PUSH_BUTTON_OK
  def _printGraph(self,**kwargs):
    G=self.G
    awayButtonsAll=kwargs.get('awayButtons',[])
    useless=kwargs.get('useless',[])
    fname=kwargs.get('fname','graph')
    with open(fname+'.dot','wb') as f:
      f.write('digraph buttonsTree {\n')
      for a in G.nodes():
        node=G.node[a]
        h=node['h']
        buttons=h[2]
        awayButtonsNode=[ b for b in buttons if b in awayButtonsAll ]
        bts        =printArray( arr_sub(buttons,awayButtonsNode+useless) )
        awayButtons=printArray( awayButtonsNode )
        useless2    =printArray( [b for b in buttons if b in useless] )
        lostButtons=node.get('lostButtons')
        label="id={idx}\\nhashPage={hashPage}\\n\
              nhref={nhref}\\nbuttons={buttons}\\n\
              awayButtons={awayButtons}\\nuseless={useless}".format(
          idx=a,
          hashPage=h[0],
          nhref=h[1],
          buttons=bts,
          awayButtons=awayButtons,
          useless=useless2,
          )
        if lostButtons:
          label+='\\nlostButtons={lostButtons}'.format(lostButtons=lostButtons)
        label=re.sub('\[','\[',label)
        label=re.sub('\]','\]',label)
        f.write('{node} [label="{label}"];\n'.format(node=a,label=label))
      for (a,b) in G.edges():
        edgeAttrib=G[a][b]
        #label='{}'.format( printArray(edgeAttrib['buttonId']) )
        label=''
        for hist in G[a][b]['hist']:
          pIdx=hist['idx']
          pN=hist['n']
          bid=self.pushHist[pIdx]
          hi=self.pushHist[pIdx-pN:pIdx]
          strHi=''
          for i in hi:
            strHi+='{},'.format(i)
          if pN>0:
            strHi=strHi[:-1]
          label+='{};{}\\n'.format(bid,strHi)
        label=re.sub('\[','\[',label)
        label=re.sub('\]','\]',label)
        f.write('{a} -> {b} [label="{label}"];\n'.format(a=a,b=b,label=label) )
    
      #write legend
      if 'buttons' in kwargs and len(kwargs['buttons']):
        buttons=kwargs['buttons']
        #buttons.sort(lambda x,y: x[0]-y[0])
        f.write('  { rank = sink;\n')
        f.write('    Legend [shape=none, margin=0, label=<\n')
        f.write('    <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">\n')
        k=buttons.keys()
        k.sort( lambda x,y: int(x)-int(y) )
        for bid in k:
          B=buttons[bid]
          if 'img' in B:
            basedir='cf-graph'
            if not os.path.exists(basedir):
              os.makedirs(basedir)
            filename='{}/button-{}.png'.format(basedir,bid)
            fimg=open(filename,'wb')
            fimg.write(base64.b64decode(B['img']))
            fimg.close()
            line=u'      <TR><TD>{bid}</TD><TD><IMG src="{filename}" SCALE="False" /></TD></TR>\n'.format(bid=bid,filename=filename)
          else:
            txt=''
            Btxt=B['features']['text']
            for i in range(len(Btxt)):
              txt+=Btxt[i]
              if i>0 and i%40==0:
                txt+='<br/>'
            line=u'      <TR><TD>{bid}</TD><TD>"{text}"</TD></TR>\n'.format(bid=bid,text=txt)
          f.write(line.encode("UTF-8"))
        f.write('  </TABLE>\n')
        f.write('  >]\n')
        f.write('  }\n')
      f.write('}\n')
    os.system('dot -Tpng {}.dot -o {}.png'.format(fname,fname))
    #print 'print graph {}.png\n'.format(fname)
    #print G.nodes()
    #print G.edges()
  def printGraph(self,**kwargs):
    self._printGraph(buttons=self.buttons,awayButtons=self.away_buttons,useless=self.getUseless() ,**kwargs)
  def traversePage(self):
    d1=datetime.datetime.now()
    self.log('START STRAVERSE: ({}) {}\n'.format(self.pageUrl,str(d1)))
    res=self._traversePage()
    self.freezeDoc('false')
    print ''
    d2=datetime.datetime.now()
    self.log('PUSH HISTORY: {}\n'.format(self.pushHist))
    self.log('START STRAVERSE: ({}) {}\n'.format(self.pageUrl,str(d1)))
    self.log('STOP TRAVERSE:   ({}) {}\n'.format(self.pageUrl,str(d2)))
    self.log('DURATION: {}\n'.format( str(d2-d1) ))
    #self.saveHrefs()
    return res
  def _traversePage(self):
    # return:
    #   TRAVERSE_OK
    #   TRAVERSE_EXCEPT
    #   TRAVERSE_NOTEND
    fname='dump-graph'
    self.getHrefs()
    #sys.stdout.write('\n')
#    try:
    if True:
      for buttonNumber in range(self.n_pushbuttons_max):
        bid=self.getButtonId()
        sys.stdout.write('\rpage: {page}    pushed buttons: {bn}  push:{bid}        '.format(page=self.pageUrl,bn=buttonNumber,bid=bid))
        sys.stdout.flush()
        if bid in self.away_buttons:
          #simple check
          #self.saveHrefs()
          self.log('getButtonId return bid={}, and bid in away_buttons\n'.format(bid))
          raise Exception
        elif bid==NOT_FOUND:
          return (TRAVERSE_OK,self.hrefs)
        res=self.pushButton(bid)
        self.saveButtons()
        self.pruneGrownLists()
#    except Exception as ex:
#      self.log('traverse failed, produce {fname}\n'.format(fname=fname) )
#      traceback.print_exc(None,self.logfile)
#      traceback.print_exc()
#      self.printGraph(fname=fname)
#      self.saveButtons()
#      return (TRAVERSE_EXCEPT,self.hrefs)
    self.saveButtons()
    bid=self.getButtonId()
    if bid==NOT_FOUND:
      #all buttons done
      return (TRAVERSE_OK,self.hrefs)
    else:
      return (TRAVERSE_NOTEND,self.hrefs)
  def pruneGrownLists(self):
    self.execute_script('cfPage.pruneTree();')
  def findUslessButtons(self):
    raise Exception
  def makeShortName(self,url):
    arr=url.split('/')
    s=arr[2].split('.')
    shortName='{}_{}'.format(s[-2],s[-1])
    return shortName
  def saveButtons(self):
    client=self.client
    cacheDir='.cache'
    siteCatalog=self.makeShortName(self.pageUrl)
    siteDir='{}/{}'.format(cacheDir,siteCatalog)
    buttonsFname='{}/buttons.json'.format(siteDir)
    buttons2=[]
    buttons=self.buttons
    for key in buttons:
      b=buttons[key]
      if 'updateImg' in b:
        b2=b.copy()
        del b2['updateImg']
        buttons2.append(b2)
      else:
        buttons2.append(b)
    new_buttons_json=json.dumps(buttons2, ensure_ascii=False, indent=4).encode('utf8')
    if not os.path.exists(siteDir):
      os.makedirs(siteDir)
    with open(buttonsFname,'wb') as fButtons:
      fButtons.write(new_buttons_json)
    self.log('save buttons to {}\n'.format(buttonsFname))
  def getHrefs(self):
    client=self.client
    hrefs=self.hrefs
    stat={'oldHrefs':0,'newHrefs':0}
    newHrefs=self.execute_script('return getSelfHrefs("all",browser.contentDocument,"{}",cfPage.layer);'.format(self.pageUrl))
    for href in newHrefs:
      if href in hrefs:
        stat['oldHrefs']+=1
      else:
        stat['newHrefs']+=1
        hrefs.append(href)
    self.log('STATITICS HREFS: old={} new={}\n'.format(stat['oldHrefs'],stat['newHrefs']))
    return stat
  def saveHrefs(self):
    hrefs=self.hrefs
    hrefs_fname=self.hrefs_fname
    self.log('save hrefs to {}\n'.format(hrefs_fname))
    with open(hrefs_fname,'wb') as f:
      for href in hrefs:
        f.write(href.encode("UTF-8"))
        if len(href)>0 and href[-1] != '\n':
          f.write('\n')
  def initHrefs(self):
    hrefs=self.hrefs
    hrefs_fname=self.hrefs_fname
    if os.path.exists(hrefs_fname):
      self.log('reading {}...'.format(hrefs_fname))
      with open(hrefs_fname,'rb') as f:
        for href in f.readlines():
          if len(href)==0:
            continue
          if href[-1]=='\n':
            href=href[:-1]
          hrefs.append(href)
      self.log('ok\n')
  def selfHref(self,href):
    pageUrl=self.pageUrl
    s1=pageUrl.split('/')[2].split('.')
    s2=href.split('/')[2].split('.')
    return s1==s2
    #return (s1[-1]==s2[-1]) and (s1[-2]==s2[-2])
  def getUseless(self):
    stats=self.stats
    useless=[]
    for cf_id in stats:
      if self.uselessPredicate(cf_id):
        useless.append( cf_id )
    return useless

def traverse(startHref,**kwargs):
  #if len(startHref)>0 and startHref[-1]!='/':
  #  startHref+='/'
  n_pushbuttons_max=kwargs.get('n_pushbuttons_max',300)
  n_process_max=kwargs.get('n_process_max')
  print_graph=kwargs.get('print_graph',False)
  nam=startHref.split('/')[2].split('.')
  sname='{}_{}'.format(nam[-2],nam[-1]) #"http://www.mk.ru" ---> "mk_ru"
  if print_graph:
    graph_path='log/{}'.format(sname)
    if not os.path.exists(graph_path):
      os.makedirs(graph_path)
  hdir='hrefs/{sname}'.format(sname=sname)
  hrefs_fname='{hdir}/hrefs.txt'.format(hdir=hdir)
  phrefs_fname='{hdir}/phrefs.txt'.format(hdir=hdir)
  log_fname='log/traverse_{}.log'.format(sname)
  if not os.path.exists('log'):
    os.makedirs('log')
  if not os.path.exists(hdir):
    os.makedirs(hdir)
  logfile=open(log_fname,'a',0)
  logfile.write('\n\n'+str(datetime.datetime.now())+'\n')
  np_hrefs=[] #not processed
  p_hrefs=[]  #processed
  if os.path.exists(phrefs_fname):
    phrefs_file=open(phrefs_fname,'r')
    for phref in phrefs_file.readline():
      if phref not in p_hrefs:
        if len(phref) and phref[-1]=='\n':
          phref=phref[:-1]
        p_hrefs.append(phref)
    phrefs_file.close()
  if os.path.exists(hrefs_fname):
    hrefs_file=open(hrefs_fname,'r')
    for href in hrefs_file.readline():
      if href not in p_hrefs and href not in np_hrefs:
        if len(href) and href[-1]=='\n':
          href=href[:-1]
        np_hrefs.append(href)
    hrefs_file.close()
  if startHref in np_hrefs:
    np_hrefs.remove(startHref)
  np_hrefs.insert(0,startHref)

  phrefs_file=open(phrefs_fname,'a')
  hrefs_file =open( hrefs_fname,'a')


  n_process=0
  while len(np_hrefs)>0:
    href=np_hrefs.pop(0)
    test1=href.split('/')
    if len(test1) < 3:
      sys.stdout.write('BAD href: {}\n'.format(href))
      continue
    test2=test1[2].split('.')
    if len(test2)<2:
      sys.stdout.write('BAD href: {}\n'.format(href))
      continue
    if href not in p_hrefs:
      p_hrefs.append(href)
      phrefs_file.write(href+'\n')
    logmsg='traverse {}\n'.format(href)
    sys.stdout.write(logmsg)
    logfile.write(logmsg)
    g=ButtonsGraph(href,**kwargs)
    status,fetched_hrefs=g.traversePage()
    n_new_hrefs=0
    for fhref in fetched_hrefs:
      if (fhref not in np_hrefs) and (fhref not in p_hrefs):
        hrefs_file.write(fhref+'\n')
        np_hrefs.append(fhref)
        n_new_hrefs+=1
    logmsg='return status: {}, fetched new hrefs: {}\n'.format(TRAVERSE_MSG[status],n_new_hrefs)
    logfile.write(logmsg)
    sys.stdout.write(logmsg)
    if print_graph:
      grFname='{}/{}'.format(graph_path,makeFname(href))
      g.printGraph(fname=grFname)
    n_process+=1
    if n_process_max and n_process >= n_process_max:
      break;

  logfile.close()
  phrefs_file.close()
  hrefs_file.close()



if __name__ == "__main__":
  tst=range(200)
  tst.pop(5)
  #action2()
  #         'http://www.mk.ru/rss/'
  #traverse('http://www.mk.ru/news',n_process_max=1,print_graph=True,n_pushbuttons_max=30,ignByCfid=ignByCfid_mk_ru)
  traverse('https://ria.ru/lenta/',n_process_max=1,print_graph=True,n_pushbuttons_max=30,ignByCfid=tst)
  #traverse('http://www.mk.ru/politics/2016/09/20/lukashenko-obvinil-rossiyu-v-ekonomicheskom-davlenii-eto-uzhe-cherez-kray.html',n_process_max=1,print_graph=True,n_pushbuttons_max=300,ignByCfid=ignByCfid_mk_ru)
  #traverse('http://www.mk.ru/incident/2016/09/20/zhena-boyarskogo-rasskazala-ob-alibi-muzha-v-moment-ubiystva-zhilina.html',n_process_max=100,print_graph=True,n_pushbuttons_max=300,ignByCfid=ignByCfid_mk_ru)

